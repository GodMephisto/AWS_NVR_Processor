import json
import os
import logging
import urllib.parse
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logger.info("normalizer build: 2025-08-13 amcrest-optimized")

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")

BUCKET = os.environ["BUCKET"]
INDEXER_FUNCTION = os.environ["INDEXER_FUNCTION"]  # function name, not ARN

# Prefer metadata; fallback to 'unknown'
ALIASES = {
    "site_id": ["site_id", "siteid", "site-id"],
    "camera_id": ["camera_id", "cameraid", "camera-id"],
}

def _pick(meta: dict, logical_key: str):
    for k in ALIASES.get(logical_key, []):
        v = meta.get(k)
        if v:
            return v
    return None

def _utc_datestring(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y/%m/%d")

def lambda_handler(event, _ctx):
    try:
        logger.info("normalize_event: %s", json.dumps(event)[:1200])
    except Exception:
        pass
    
    for rec in event.get("Records", []):
        if rec.get("eventSource") != "aws:s3":
            continue
        
        bkt = rec["s3"]["bucket"]["name"]
        key = urllib.parse.unquote(rec["s3"]["object"]["key"])
        
        # Already normalized -> just invoke indexer
        if key.startswith("cctv/"):
            _invoke_indexer_passthru(rec, bkt, key)
            continue
        
        # Head source object
        try:
            head = s3.head_object(Bucket=bkt, Key=key)
        except ClientError as e:
            logger.warning("head_object failed for s3://%s/%s: %s", bkt, key, e)
            continue
        
        meta = {k.lower(): v for k, v in (head.get("Metadata") or {}).items()}
        site = _pick(meta, "site_id") or "unknown"
        cam = _pick(meta, "camera_id") or "unknown"
        
        # Prefer eventTime; fallback to LastModified; else now()
        when = None
        ev_time = rec.get("eventTime")
        if ev_time:
            try:
                when = datetime.fromisoformat(ev_time.replace("Z", "+00:00"))
            except Exception:
                when = None
        
        if when is None:
            lm = head.get("LastModified")
            when = lm if isinstance(lm, datetime) else datetime.now(timezone.utc)
        
        date_prefix = _utc_datestring(when)  # YYYY/MM/DD
        filename = key.split("/")[-1]
        norm_key = f"cctv/{site}/{cam}/{date_prefix}/{filename}"
        
        if norm_key == key:
            _invoke_indexer_passthru(rec, bkt, key)
            continue
        
        # Idempotent copy: if destination already exists, SKIP copy AND SKIP invoking indexer.
        try:
            s3.head_object(Bucket=BUCKET, Key=norm_key)
            logger.info("normalized exists (skip copy & index): %s", norm_key)
            continue
        except ClientError as e:
            code = (e.response.get("Error") or {}).get("Code")
            if code not in ("404", "NoSuchKey"):
                logger.error("head_object failed for %s: %s", norm_key, e)
                continue
        
        # Destination not found -> copy
        try:
            s3.copy_object(
                Bucket=BUCKET,
                Key=norm_key,
                CopySource={"Bucket": bkt, "Key": key},
                MetadataDirective="COPY",
            )
            logger.info("normalized: %s -> %s", key, norm_key)
        except ClientError as e:
            logger.error("copy_object failed %s -> %s: %s", key, norm_key, e)
            continue
        
        # S3 will emit ObjectCreated:Copy for norm_key; on that event (key startswith 'cctv/'),
        # this function will invoke the indexer.
    
    return {"statusCode": 200, "body": json.dumps({"ok": True})}

def _invoke_indexer_passthru(orig_rec, bucket, key):
    """Invoke the existing indexer with a minimal S3-like event."""
    payload = {
        "Records": [{
            "eventSource": "aws:s3",
            "eventName": orig_rec.get("eventName", "ObjectCreated:Put"),
            "eventTime": orig_rec.get("eventTime"),
            "s3": {
                "bucket": {"name": bucket},
                "object": {"key": key}
            }
        }]
    }
    
    try:
        lambda_client.invoke(
            FunctionName=INDEXER_FUNCTION,
            InvocationType="Event",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        logger.info("invoked indexer for s3://%s/%s", bucket, key)
    except ClientError as e:
        logger.error("invoke indexer failed: %s", e)