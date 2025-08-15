"""
Cloud Synchronization Service
Handles uploading video files and metadata to AWS S3 with intelligent bandwidth management
"""

import boto3
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
from botocore.exceptions import ClientError, NoCredentialsError

from ..config.nvr_config import config

@dataclass
class SyncTask:
 """Represents a file synchronization task"""
 local_path: str
 s3_key: str
 camera_id: str
 site_id: str
 priority: int = 1 # 1=normal, 2=high (motion detected), 3=critical
 retry_count: int = 0
 created_at: datetime = None

 def __post_init__(self):
 if self.created_at is None:
 self.created_at = datetime.now(timezone.utc)

@dataclass
class SyncResult:
 """Result of a synchronization operation"""
 success: bool
 task: SyncTask
 error_message: str = ""
 upload_time_seconds: float = 0.0
 bytes_uploaded: int = 0

class BandwidthMonitor:
 """Monitors and controls upload bandwidth usage"""

 def __init__(self, max_bandwidth_mbps: int = 10):
 self.max_bandwidth_mbps = max_bandwidth_mbps
 self.max_bytes_per_second = max_bandwidth_mbps * 1024 * 1024 / 8
 self.upload_history = [] # List of (timestamp, bytes) tuples
 self.history_window = 60 # seconds
 self.lock = threading.Lock()

 def record_upload(self, bytes_uploaded: int) -> None:
 """Record bytes uploaded"""
 with self.lock:
 now = time.time()
 self.upload_history.append((now, bytes_uploaded))

 # Clean old entries
 cutoff = now - self.history_window
 self.upload_history = [(t, b) for t, b in self.upload_history if t > cutoff]

 def get_current_bandwidth_usage(self) -> float:
 """Get current bandwidth usage in bytes per second"""
 with self.lock:
 if not self.upload_history:
 return 0.0

 now = time.time()
 cutoff = now - self.history_window

 recent_uploads = [(t, b) for t, b in self.upload_history if t > cutoff]
 if not recent_uploads:
 return 0.0

 total_bytes = sum(b for _, b in recent_uploads)
 time_span = now - recent_uploads[0][0]

 return total_bytes / max(time_span, 1.0)

 def should_throttle(self) -> bool:
 """Check if uploads should be throttled"""
 current_usage = self.get_current_bandwidth_usage()
 return current_usage > self.max_bytes_per_second

 def get_throttle_delay(self) -> float:
 """Get delay in seconds to throttle bandwidth"""
 if not self.should_throttle():
 return 0.0

 current_usage = self.get_current_bandwidth_usage()
 excess_ratio = current_usage / self.max_bytes_per_second

 # Exponential backoff based on excess usage
 return min(excess_ratio * 2.0, 10.0)

class CloudSyncService:
 """Service for synchronizing video files to AWS S3"""

 def __init__(self):
 self.logger = logging.getLogger(__name__)
 self.s3_client = None
 self.sync_queue: List[SyncTask] = []
 self.bandwidth_monitor = BandwidthMonitor(config.sync.max_bandwidth_mbps)

 # Threading
 self.sync_thread: Optional[threading.Thread] = None
 self.running = False
 self.queue_lock = threading.Lock()

 # Statistics
 self.total_uploads = 0
 self.successful_uploads = 0
 self.failed_uploads = 0
 self.total_bytes_uploaded = 0
 self.total_upload_time = 0.0

 # Initialize AWS client
 self._initialize_aws_client()

 def _initialize_aws_client(self) -> None:
 """Initialize AWS S3 client"""
 try:
 self.s3_client = boto3.client(
 's3',
 region_name=config.aws.region,
 aws_access_key_id=config.aws.access_key_id,
 aws_secret_access_key=config.aws.secret_access_key
 )

 # Test connection
 self.s3_client.head_bucket(Bucket=config.aws.bucket_name)
 self.logger.info("AWS S3 client initialized successfully")

 except NoCredentialsError:
 self.logger.error("AWS credentials not configured")
 self.s3_client = None
 except ClientError as e:
 self.logger.error(f"Failed to initialize AWS S3 client: {e}")
 self.s3_client = None
 except Exception as e:
 self.logger.error(f"Unexpected error initializing AWS client: {e}")
 self.s3_client = None

 def start(self) -> None:
 """Start the cloud synchronization service"""
 if self.running:
 self.logger.warning("Cloud sync service already running")
 return

 if not self.s3_client:
 self.logger.error("Cannot start sync service: AWS client not initialized")
 return

 self.running = True
 self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
 self.sync_thread.start()

 self.logger.info("Cloud synchronization service started")

 def stop(self) -> None:
 """Stop the cloud synchronization service"""
 self.running = False

 if self.sync_thread and self.sync_thread.is_alive():
 self.sync_thread.join(timeout=30.0)

 self.logger.info("Cloud synchronization service stopped")

 def queue_file_for_sync(self, local_path: str, camera_id: str, site_id: str,
 priority: int = 1, has_motion: bool = False, metadata: Optional[Dict] = None) -> None:
 """Queue a file for synchronization to S3"""
 try:
 # Generate S3 key based on site/camera/date structure
 file_path = Path(local_path)
 filename = file_path.name

 # Use current date for organization
 now = datetime.now(timezone.utc)
 date_prefix = now.strftime("%Y/%m/%d")

 s3_key = f"cctv/{site_id}/{camera_id}/{date_prefix}/{filename}"

 # Set priority based on motion detection
 if has_motion:
 priority = max(priority, 2) # High priority for motion videos

 task = SyncTask(
 local_path=local_path,
 s3_key=s3_key,
 camera_id=camera_id,
 site_id=site_id,
 priority=priority
 )

 with self.queue_lock:
 self.sync_queue.append(task)
 # Sort by priority (higher priority first)
 self.sync_queue.sort(key=lambda t: t.priority, reverse=True)

 self.logger.debug(f"Queued file for sync: {local_path} -> s3://{config.aws.bucket_name}/{s3_key}")

 except Exception as e:
 self.logger.error(f"Failed to queue file for sync: {e}")

 def _sync_loop(self) -> None:
 """Main synchronization loop"""
 while self.running:
 try:
 # Check if we should throttle
 if self.bandwidth_monitor.should_throttle():
 delay = self.bandwidth_monitor.get_throttle_delay()
 self.logger.debug(f"Throttling uploads for {delay:.1f}s")
 time.sleep(delay)
 continue

 # Get next task
 task = None
 with self.queue_lock:
 if self.sync_queue:
 task = self.sync_queue.pop(0)

 if not task:
 time.sleep(1.0)
 continue

 # Process the task
 result = self._sync_file(task)
 self._handle_sync_result(result)

 except Exception as e:
 self.logger.error(f"Sync loop error: {e}")
 time.sleep(5.0)

 def _sync_file(self, task: SyncTask) -> SyncResult:
 """Synchronize a single file to S3"""
 start_time = time.time()

 try:
 # Check if file exists
 if not Path(task.local_path).exists():
 return SyncResult(
 success=False,
 task=task,
 error_message="Local file not found"
 )

 # Get file size
 file_size = Path(task.local_path).stat().st_size

 # Check if file already exists in S3
 try:
 self.s3_client.head_object(Bucket=config.aws.bucket_name, Key=task.s3_key)
 self.logger.debug(f"File already exists in S3: {task.s3_key}")
 return SyncResult(
 success=True,
 task=task,
 bytes_uploaded=0,
 upload_time_seconds=time.time() - start_time
 )
 except ClientError as e:
 if e.response['Error']['Code'] != '404':
 raise

 # Load metadata if available
 metadata_path = Path(task.local_path).with_suffix('.metadata.json')
 s3_metadata = {}

 if metadata_path.exists():
 try:
 with open(metadata_path, 'r') as f:
 metadata = json.load(f)

 # Convert to S3 metadata headers for Lambda indexer compatibility
 s3_metadata = {
 'site_id': task.site_id,
 'camera_id': task.camera_id,
 'start_ts': metadata.get('start_timestamp', ''),
 'end_ts': metadata.get('end_timestamp', ''),
 'duration_sec': str(int(float(metadata.get('duration', 0)))),
 'motion_percentage': str(metadata.get('motion_percentage', 0)),
 'motion_events': str(len(metadata.get('motion_events', []))),
 'width': str(metadata.get('width', 0)),
 'height': str(metadata.get('height', 0)),
 'fps': str(metadata.get('fps', 0)),
 'codec': metadata.get('codec', 'unknown'),
 'bitrate': str(metadata.get('bitrate', 0))
 }
 except Exception as e:
 self.logger.warning(f"Failed to load metadata for {task.local_path}: {e}")

 # Upload file to S3 with multipart upload for large files
 self.logger.info(f"Uploading {task.local_path} to s3://{config.aws.bucket_name}/{task.s3_key}")

 if file_size > 100 * 1024 * 1024: # 100MB threshold for multipart
 self._multipart_upload(task.local_path, config.aws.bucket_name, task.s3_key, s3_metadata)
 else:
 self.s3_client.upload_file(
 task.local_path,
 config.aws.bucket_name,
 task.s3_key,
 ExtraArgs={'Metadata': s3_metadata} if s3_metadata else None
 )

 upload_time = time.time() - start_time

 # Record bandwidth usage
 self.bandwidth_monitor.record_upload(file_size)

 self.logger.info(f"Successfully uploaded {task.local_path} ({file_size} bytes) in {upload_time:.2f}s")

 return SyncResult(
 success=True,
 task=task,
 bytes_uploaded=file_size,
 upload_time_seconds=upload_time
 )

 except Exception as e:
 upload_time = time.time() - start_time
 error_msg = str(e)

 self.logger.error(f"Failed to upload {task.local_path}: {error_msg}")

 return SyncResult(
 success=False,
 task=task,
 error_message=error_msg,
 upload_time_seconds=upload_time
 )

 def _multipart_upload(self, local_path: str, bucket: str, key: str, metadata: Dict) -> None:
 """Upload large file using multipart upload"""
 # Create multipart upload
 response = self.s3_client.create_multipart_upload(
 Bucket=bucket,
 Key=key,
 Metadata=metadata
 )
 upload_id = response['UploadId']

 try:
 parts = []
 part_size = 100 * 1024 * 1024 # 100MB parts
 part_number = 1

 with open(local_path, 'rb') as f:
 while True:
 data = f.read(part_size)
 if not data:
 break

 # Upload part
 response = self.s3_client.upload_part(
 Bucket=bucket,
 Key=key,
 PartNumber=part_number,
 UploadId=upload_id,
 Body=data
 )

 parts.append({
 'ETag': response['ETag'],
 'PartNumber': part_number
 })

 part_number += 1

 # Record bandwidth for throttling
 self.bandwidth_monitor.record_upload(len(data))

 # Complete multipart upload
 self.s3_client.complete_multipart_upload(
 Bucket=bucket,
 Key=key,
 UploadId=upload_id,
 MultipartUpload={'Parts': parts}
 )

 except Exception as e:
 # Abort multipart upload on error
 try:
 self.s3_client.abort_multipart_upload(
 Bucket=bucket,
 Key=key,
 UploadId=upload_id
 )
 except Exception:
 pass
 raise e

 def _handle_sync_result(self, result: SyncResult) -> None:
 """Handle the result of a sync operation"""
 self.total_uploads += 1
 self.total_upload_time += result.upload_time_seconds

 if result.success:
 self.successful_uploads += 1
 self.total_bytes_uploaded += result.bytes_uploaded

 # Mark local file as synced (add .synced marker)
 try:
 synced_marker = Path(result.task.local_path).with_suffix('.synced')
 synced_marker.touch()
 except Exception as e:
 self.logger.warning(f"Failed to create sync marker: {e}")
 else:
 self.failed_uploads += 1

 # Retry logic
 if result.task.retry_count < config.sync.retry_attempts:
 result.task.retry_count += 1

 # Exponential backoff
 delay = min(2 ** result.task.retry_count, 300) # Max 5 minutes

 # Re-queue with delay
 def retry_task():
 time.sleep(delay)
 with self.queue_lock:
 self.sync_queue.append(result.task)
 self.sync_queue.sort(key=lambda t: t.priority, reverse=True)

 retry_thread = threading.Thread(target=retry_task, daemon=True)
 retry_thread.start()

 self.logger.info(f"Retrying upload in {delay}s (attempt {result.task.retry_count}/{config.sync.retry_attempts})")
 else:
 self.logger.error(f"Max retries exceeded for {result.task.local_path}")

 def get_queue_status(self) -> Dict:
 """Get current queue status"""
 with self.queue_lock:
 queue_by_priority = {}
 for task in self.sync_queue:
 priority = task.priority
 if priority not in queue_by_priority:
 queue_by_priority[priority] = 0
 queue_by_priority[priority] += 1

 return {
 'total_queued': len(self.sync_queue),
 'by_priority': queue_by_priority,
 'bandwidth_usage_mbps': self.bandwidth_monitor.get_current_bandwidth_usage() * 8 / (1024 * 1024),
 'is_throttling': self.bandwidth_monitor.should_throttle()
 }

 def get_statistics(self) -> Dict:
 """Get service statistics"""
 return {
 'running': self.running,
 'total_uploads': self.total_uploads,
 'successful_uploads': self.successful_uploads,
 'failed_uploads': self.failed_uploads,
 'success_rate': (self.successful_uploads / self.total_uploads * 100) if self.total_uploads > 0 else 0,
 'total_bytes_uploaded': self.total_bytes_uploaded,
 'total_upload_time': self.total_upload_time,
 'average_upload_speed_mbps': (
 (self.total_bytes_uploaded * 8) / (self.total_upload_time * 1024 * 1024)
 if self.total_upload_time > 0 else 0
 ),
 'queue_status': self.get_queue_status()
 }

 def force_sync_file(self, local_path: str, camera_id: str, site_id: str) -> bool:
 """Force immediate synchronization of a file (blocking)"""
 try:
 # Create high priority task
 task = SyncTask(
 local_path=local_path,
 s3_key=f"cctv/{site_id}/{camera_id}/{Path(local_path).name}",
 camera_id=camera_id,
 site_id=site_id,
 priority=3 # Critical priority
 )

 # Sync immediately
 result = self._sync_file(task)
 self._handle_sync_result(result)

 return result.success

 except Exception as e:
 self.logger.error(f"Force sync failed for {local_path}: {e}")
 return False

# Global cloud sync service instance
cloud_sync_service = CloudSyncService()