import os
import json
import re
import time
import logging
import urllib.parse
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

# =========================
# Config / Clients
# =========================
BUCKET = os.environ["BUCKET"]
TABLE = os.environ["TABLE"]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logger.info("indexer build: 2025-08-13 amcrest-optimized")

s3 = boto3.client("s3")
ddb = boto3.client("dynamodb")

ALIASES = {
    "site_id": ["site_id", "siteid", "site-id"],
    "camera_id": ["camera_id", "cameraid", "camera-id"],
    "start_ts": ["start_ts", "startts", "start-ts"],
    "end_ts": ["end_ts", "endts", "end-ts"],
    "duration_sec": ["duration_sec", "durationsec", "duration-sec"],
}

# Amcrest filename patterns
RE_AMCREST = re.compile(r"ch(?P<ch>\d{1,2})[_-]?(?P<ts>\d{14})")  # ch1_20250814123045
RE_ISO = re.compile(r"(?P<iso>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")
RE_COMPACT = re.compile(r"(?P<iso_compact>\d{8}T\d{6}Z)")

def _pick(meta: dict, logical_key: str):
    for k in ALIASES[logical_key]:
        v = meta.get(k)
        if v:
            return v
    return None

def _to_utc_iso(ts: str) -> str | None:
    """Return ISO-8601 Zulu string; return None on parse failure."""
    if not ts:
        return None
    try:
        if isinstance(ts, datetime):
            dt = ts.astimezone(timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        
        t = ts.strip().replace(" ", "T")
        if t.endswith("Z"):
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        elif "+" in t or "-" in t[10:]:
            dt = datetime.fromisoformat(t)
        else:
            dt = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception as e:
        logger.debug("to_utc_iso parse failed for %s (%s)", ts, e)
        return None

def _extract_from_filename(filename: str) -> str | None:
    """Parse timestamp from filename using Amcrest patterns."""
    # Try Amcrest pattern first
    m = RE_AMCREST.search(filename)
    if m:
        ts = m.group("ts")
        try:
            # Format: YYYYMMDDHHMMSS
            start = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            return start.isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    
    # Try ISO patterns
    m = RE_ISO.search(filename)
    if m:
        return _to_utc_iso(m.group("iso"))
    
    m = RE_COMPACT.search(filename)
    if m:
        v = m.group("iso_compact")
        expanded = f"{v[0:4]}-{v[4:6]}-{v[6:8]}T{v[9:11]}:{v[11:13]}:{v[13:15]}Z"
        return _to_utc_iso(expanded)
    
    return None

def _guess_start_ts(meta, filename, rec, head):
    """Return (iso_ts, source) or (None, None) if none found."""
    ts = _pick(meta, "start_ts")
    iso = _to_utc_iso(ts) if ts else None
    if iso:
        return iso, "meta"
    
    iso = _extract_from_filename(filename)
    if iso:
        return iso, "filename"
    
    event_time = rec.get("eventTime")
    iso = _to_utc_iso(event_time) if event_time else None
    if iso:
        return iso, "eventTime"
    
    last_mod = head.get("LastModified")
    iso = _to_utc_iso(last_mod) if last_mod else None
    if iso:
        return iso, "lastModified"
    
    return None, None

def _put_item_idempotent(item: dict, retries: int = 3) -> bool:
    backoff = 0.25
    for attempt in range(1, retries + 1):
        try:
            ddb.put_item(
                TableName=TABLE,
                Item=item,
                ConditionExpression="attribute_not_exists(camera_id) AND attribute_not_exists(start_ts)",
            )
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code == "ConditionalCheckFailedException":
                logger.info("Item already exists (idempotent put): %s %s",
                           item.get("camera_id", {}).get("S"),
                           item.get("start_ts", {}).get("S"),
                )
                return False
            elif code in {
                "ProvisionedThroughputExceededException",
                "ThrottlingException",
                "InternalServerError",
            }:
                logger.warning("DDB transient error (%s), attempt %d/%d; backing off %.2fs",
                              code, attempt, retries, backoff)
                time.sleep(backoff)
                backoff *= 2
                continue
            
            logger.exception("DDB put_item failed (non-retryable): %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error in put_item: %s", e)
            raise
    
    logger.error("DDB put_item exhausted retries")
    return False

def lambda_handler(event, ctx):
    logger.info("received_event: %s", json.dumps(event)[:2000])
    count = 0
    
    for rec in event.get("Records", []):
        if rec.get("eventSource") != "aws:s3":
            continue
        
        bkt = rec["s3"]["bucket"]["name"]
        key = urllib.parse.unquote(rec["s3"]["object"]["key"])
        evn = rec.get("eventName", "unknown")
        
        logger.info("s3_event: %s s3://%s/%s", evn, bkt, key)
        
        if bkt != BUCKET or not key.startswith("cctv/"):
            logger.debug("skip (unexpected bucket/prefix): %s %s", bkt, key)
            continue
        
        try:
            head = s3.head_object(Bucket=bkt, Key=key)
        except ClientError as e:
            logger.warning("head_object failed: %s", e)
            continue
        
        meta = {k.lower(): v for k, v in (head.get("Metadata") or {}).items()}
        size = head.get("ContentLength", 0)
        sc = head.get("StorageClass", "STANDARD") or "STANDARD"
        etag = (head.get("ETag") or "").strip('"')
        restore_hdr = head.get("Restore")
        
        parts = key.split("/")
        site_from_path = parts[1] if len(parts) > 1 else "unknown"
        camera_from_path = parts[2] if len(parts) > 2 else "unknown"
        filename = parts[-1]
        
        site_id = _pick(meta, "site_id") or site_from_path
        camera_id = _pick(meta, "camera_id") or camera_from_path
        
        start_ts, source = _guess_start_ts(meta, filename, rec, head)
        if not start_ts:
            logger.warning("no valid timestamp found; skipping: %s", key)
            continue
        
        end_ts = _to_utc_iso(_pick(meta, "end_ts") or "")
        duration = _pick(meta, "duration_sec")
        
        item = {
            "camera_id": {"S": camera_id or "unknown"},
            "start_ts": {"S": start_ts},
            "s3_key": {"S": key},
            "site_id": {"S": site_id or "unknown"},
            "size": {"N": str(int(size)) if isinstance(size, int) else str(size)},
            "storage_class": {"S": sc},
            "etag": {"S": etag},
            "ts_source": {"S": source},
        }
        
        if duration:
            try:
                item["duration_sec"] = {"N": str(int(float(duration)))}
            except Exception:
                logger.debug("invalid duration_sec: %s", duration)
        
        if end_ts:
            item["end_ts"] = {"S": end_ts}
        
        if restore_hdr:
            item["restore"] = {"S": restore_hdr}
        
        logger.info("put_item keys: camera_id=%s start_ts=%s source=%s",
                   item["camera_id"]["S"], item["start_ts"]["S"], source)
        
        if _put_item_idempotent(item):
            count += 1
    
    result = {"ok": True, "count": count}
    logger.info("result: %s", result)
    return {"statusCode": 200, "body": json.dumps(result)}