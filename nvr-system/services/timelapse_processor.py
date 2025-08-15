"""
Timelapse Processing Service
Converts videos older than 30 days into compressed timelapses for long-term storage optimization
"""

import cv2
import json
import logging
import os
import threading
import time
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError

from ..config.nvr_config import config
from .metadata_extractor import MetadataExtractor

@dataclass
class TimelapseJob:
 """Represents a timelapse conversion job"""
 original_s3_key: str
 original_local_path: str
 timelapse_s3_key: str
 timelapse_local_path: str
 camera_id: str
 site_id: str
 original_duration: float
 target_duration: float
 frame_sampling_rate: int # Take 1 frame every N frames
 created_at: datetime

@dataclass
class TimelapseResult:
 """Result of timelapse conversion"""
 success: bool
 job: TimelapseJob
 original_size_bytes: int
 timelapse_size_bytes: int
 compression_ratio: float
 processing_time_seconds: float
 error_message: str = ""

class TimelapseProcessor:
 """Processes videos into timelapses with motion-based frame selection"""

 def __init__(self):
 self.logger = logging.getLogger(__name__)
 self.metadata_extractor = MetadataExtractor()

 # Motion detection for intelligent frame selection
 self.motion_detector = cv2.createBackgroundSubtractorMOG2(
 detectShadows=True,
 varThreshold=16,
 history=500
 )

 def create_timelapse(self, job: TimelapseJob) -> TimelapseResult:
 """Create timelapse from original video"""
 start_time = time.time()

 try:
 # Check if original file exists
 if not Path(job.original_local_path).exists():
 return TimelapseResult(
 success=False,
 job=job,
 original_size_bytes=0,
 timelapse_size_bytes=0,
 compression_ratio=0.0,
 processing_time_seconds=time.time() - start_time,
 error_message="Original file not found"
 )

 original_size = Path(job.original_local_path).stat().st_size

 # Open original video
 cap = cv2.VideoCapture(job.original_local_path)
 if not cap.isOpened():
 return TimelapseResult(
 success=False,
 job=job,
 original_size_bytes=original_size,
 timelapse_size_bytes=0,
 compression_ratio=0.0,
 processing_time_seconds=time.time() - start_time,
 error_message="Cannot open original video"
 )

 # Get video properties
 original_fps = cap.get(cv2.CAP_PROP_FPS)
 frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
 width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
 height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

 # Calculate timelapse parameters
 target_fps = 30 # Standard timelapse FPS
 total_frames_needed = int(job.target_duration * target_fps)
 frame_skip = max(1, frame_count // total_frames_needed)

 # Create timelapse with motion-based frame selection
 selected_frames = self._select_frames_with_motion(
 cap, frame_skip, total_frames_needed
 )

 cap.release()

 if not selected_frames:
 return TimelapseResult(
 success=False,
 job=job,
 original_size_bytes=original_size,
 timelapse_size_bytes=0,
 compression_ratio=0.0,
 processing_time_seconds=time.time() - start_time,
 error_message="No frames selected for timelapse"
 )

 # Create timelapse video
 timelapse_size = self._create_timelapse_video(
 job.original_local_path,
 job.timelapse_local_path,
 selected_frames,
 target_fps,
 width,
 height
 )

 if timelapse_size == 0:
 return TimelapseResult(
 success=False,
 job=job,
 original_size_bytes=original_size,
 timelapse_size_bytes=0,
 compression_ratio=0.0,
 processing_time_seconds=time.time() - start_time,
 error_message="Failed to create timelapse video"
 )

 # Calculate compression ratio
 compression_ratio = (original_size - timelapse_size) / original_size * 100

 processing_time = time.time() - start_time

 self.logger.info(
 f"Created timelapse: {job.original_local_path} -> {job.timelapse_local_path} "
 f"({original_size} -> {timelapse_size} bytes, {compression_ratio:.1f}% compression) "
 f"in {processing_time:.2f}s"
 )

 return TimelapseResult(
 success=True,
 job=job,
 original_size_bytes=original_size,
 timelapse_size_bytes=timelapse_size,
 compression_ratio=compression_ratio,
 processing_time_seconds=processing_time
 )

 except Exception as e:
 processing_time = time.time() - start_time
 error_msg = str(e)

 self.logger.error(f"Timelapse creation failed: {error_msg}")

 return TimelapseResult(
 success=False,
 job=job,
 original_size_bytes=Path(job.original_local_path).stat().st_size if Path(job.original_local_path).exists() else 0,
 timelapse_size_bytes=0,
 compression_ratio=0.0,
 processing_time_seconds=processing_time,
 error_message=error_msg
 )

 def _select_frames_with_motion(self, cap: cv2.VideoCapture, frame_skip: int, max_frames: int) -> List[int]:
 """Select frames for timelapse based on motion detection"""
 selected_frames = []
 frame_scores = [] # (frame_number, motion_score)

 frame_number = 0

 # First pass: analyze all frames for motion
 while len(frame_scores) < max_frames * 2: # Analyze more frames than needed
 cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
 ret, frame = cap.read()

 if not ret:
 break

 # Calculate motion score
 motion_mask = self.motion_detector.apply(frame)
 motion_pixels = cv2.countNonZero(motion_mask)
 total_pixels = motion_mask.shape[0] * motion_mask.shape[1]
 motion_score = motion_pixels / total_pixels

 frame_scores.append((frame_number, motion_score))
 frame_number += frame_skip

 # Second pass: select frames with highest motion scores
 if frame_scores:
 # Sort by motion score (descending) and take top frames
 frame_scores.sort(key=lambda x: x[1], reverse=True)

 # Take frames with motion, but ensure temporal distribution
 selected_frames = []
 min_frame_gap = len(frame_scores) // max_frames if frame_scores else 1

 last_selected_frame = -min_frame_gap

 for frame_num, score in frame_scores:
 if len(selected_frames) >= max_frames:
 break

 # Ensure minimum gap between selected frames
 if frame_num - last_selected_frame >= min_frame_gap:
 selected_frames.append(frame_num)
 last_selected_frame = frame_num

 # If not enough motion frames, fill with evenly spaced frames
 if len(selected_frames) < max_frames // 2:
 # Fall back to uniform sampling
 total_frames = frame_scores[-1][0] if frame_scores else 0
 uniform_skip = max(1, total_frames // max_frames)
 selected_frames = list(range(0, total_frames, uniform_skip))[:max_frames]

 # Sort selected frames by frame number
 selected_frames.sort()

 return selected_frames

 def _create_timelapse_video(self, input_path: str, output_path: str,
 frame_numbers: List[int], fps: int, width: int, height: int) -> int:
 """Create timelapse video from selected frames"""
 try:
 # Ensure output directory exists
 os.makedirs(os.path.dirname(output_path), exist_ok=True)

 # Use FFmpeg for better compression and quality
 temp_frame_dir = Path(output_path).parent / "temp_frames"
 temp_frame_dir.mkdir(exist_ok=True)

 try:
 # Extract selected frames
 cap = cv2.VideoCapture(input_path)

 for i, frame_num in enumerate(frame_numbers):
 cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
 ret, frame = cap.read()

 if ret:
 frame_path = temp_frame_dir / f"frame_{i:06d}.jpg"
 cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

 cap.release()

 # Create timelapse using FFmpeg
 ffmpeg_cmd = [
 'ffmpeg', '-y', # Overwrite output
 '-framerate', str(fps),
 '-i', str(temp_frame_dir / 'frame_%06d.jpg'),
 '-c:v', 'libx264',
 '-preset', 'medium',
 '-crf', '28', # Higher CRF for more compression
 '-pix_fmt', 'yuv420p',
 '-movflags', '+faststart',
 output_path
 ]

 result = subprocess.run(
 ffmpeg_cmd,
 capture_output=True,
 text=True,
 check=True
 )

 # Clean up temp frames
 for frame_file in temp_frame_dir.glob("*.jpg"):
 frame_file.unlink()
 temp_frame_dir.rmdir()

 # Return file size
 if Path(output_path).exists():
 return Path(output_path).stat().st_size
 else:
 return 0

 except subprocess.CalledProcessError as e:
 self.logger.error(f"FFmpeg failed: {e.stderr}")

 # Fallback to OpenCV
 return self._create_timelapse_opencv(input_path, output_path, frame_numbers, fps, width, height)

 finally:
 # Cleanup temp directory
 if temp_frame_dir.exists():
 for frame_file in temp_frame_dir.glob("*.jpg"):
 frame_file.unlink()
 try:
 temp_frame_dir.rmdir()
 except:
 pass

 except Exception as e:
 self.logger.error(f"Timelapse creation failed: {e}")
 return 0

 def _create_timelapse_opencv(self, input_path: str, output_path: str,
 frame_numbers: List[int], fps: int, width: int, height: int) -> int:
 """Fallback timelapse creation using OpenCV"""
 try:
 # Define codec and create VideoWriter
 fourcc = cv2.VideoWriter_fourcc(*'mp4v')
 out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

 cap = cv2.VideoCapture(input_path)

 for frame_num in frame_numbers:
 cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
 ret, frame = cap.read()

 if ret:
 out.write(frame)

 cap.release()
 out.release()

 # Return file size
 if Path(output_path).exists():
 return Path(output_path).stat().st_size
 else:
 return 0

 except Exception as e:
 self.logger.error(f"OpenCV timelapse creation failed: {e}")
 return 0

class TimelapseService:
 """Service for managing timelapse conversion of old videos"""

 def __init__(self):
 self.logger = logging.getLogger(__name__)
 self.processor = TimelapseProcessor()
 self.s3_client = None

 # Processing queue and threading
 self.processing_queue: List[TimelapseJob] = []
 self.processing_thread: Optional[threading.Thread] = None
 self.running = False
 self.queue_lock = threading.Lock()

 # Statistics
 self.total_processed = 0
 self.successful_conversions = 0
 self.failed_conversions = 0
 self.total_space_saved = 0
 self.total_processing_time = 0.0

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
 except Exception as e:
 self.logger.error(f"Failed to initialize AWS client: {e}")
 self.s3_client = None

 def start(self) -> None:
 """Start the timelapse service"""
 if self.running:
 self.logger.warning("Timelapse service already running")
 return

 self.running = True
 self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
 self.processing_thread.start()

 self.logger.info("Timelapse service started")

 def stop(self) -> None:
 """Stop the timelapse service"""
 self.running = False

 if self.processing_thread and self.processing_thread.is_alive():
 self.processing_thread.join(timeout=30.0)

 self.logger.info("Timelapse service stopped")

 def scan_for_old_videos(self) -> None:
 """Scan S3 for videos older than 30 days and queue for timelapse conversion"""
 if not self.s3_client:
 self.logger.error("Cannot scan S3: AWS client not initialized")
 return

 try:
 cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

 # List objects in S3 bucket
 paginator = self.s3_client.get_paginator('list_objects_v2')

 for page in paginator.paginate(Bucket=config.aws.bucket_name, Prefix='cctv/'):
 for obj in page.get('Contents', []):
 # Check if object is old enough and not already a timelapse
 if (obj['LastModified'] < cutoff_date and
 not obj['Key'].endswith('_timelapse.mp4') and
 obj['Key'].endswith(('.mp4', '.avi', '.mov', '.mkv'))):

 # Parse camera info from S3 key
 key_parts = obj['Key'].split('/')
 if len(key_parts) >= 3:
 site_id = key_parts[1]
 camera_id = key_parts[2]

 # Check if timelapse already exists
 timelapse_key = obj['Key'].replace('.mp4', '_timelapse.mp4')

 try:
 self.s3_client.head_object(Bucket=config.aws.bucket_name, Key=timelapse_key)
 continue # Timelapse already exists
 except ClientError as e:
 if e.response['Error']['Code'] != '404':
 continue

 # Queue for processing
 self._queue_timelapse_job(obj['Key'], site_id, camera_id, obj['Size'])

 self.logger.info("Completed scan for old videos")

 except Exception as e:
 self.logger.error(f"Failed to scan for old videos: {e}")

 def _queue_timelapse_job(self, s3_key: str, site_id: str, camera_id: str, file_size: int) -> None:
 """Queue a timelapse conversion job"""
 try:
 # Calculate target duration (compress to 1/60th of original for 1 hour -> 1 minute)
 estimated_duration = file_size / (10 * 1024 * 1024) # Rough estimate: 10MB per minute
 target_duration = max(30, estimated_duration / 60) # Minimum 30 seconds

 # Generate local paths
 filename = Path(s3_key).name
 timelapse_filename = filename.replace('.mp4', '_timelapse.mp4')

 local_dir = Path(config.storage.base_path) / "timelapse_processing"
 local_dir.mkdir(exist_ok=True)

 original_local_path = local_dir / filename
 timelapse_local_path = local_dir / timelapse_filename
 timelapse_s3_key = s3_key.replace('.mp4', '_timelapse.mp4')

 job = TimelapseJob(
 original_s3_key=s3_key,
 original_local_path=str(original_local_path),
 timelapse_s3_key=timelapse_s3_key,
 timelapse_local_path=str(timelapse_local_path),
 camera_id=camera_id,
 site_id=site_id,
 original_duration=estimated_duration,
 target_duration=target_duration,
 frame_sampling_rate=max(1, int(estimated_duration / target_duration)),
 created_at=datetime.now(timezone.utc)
 )

 with self.queue_lock:
 self.processing_queue.append(job)

 self.logger.debug(f"Queued timelapse job: {s3_key}")

 except Exception as e:
 self.logger.error(f"Failed to queue timelapse job for {s3_key}: {e}")

 def _processing_loop(self) -> None:
 """Main processing loop"""
 while self.running:
 try:
 # Get next job
 job = None
 with self.queue_lock:
 if self.processing_queue:
 job = self.processing_queue.pop(0)

 if not job:
 time.sleep(10.0) # Check every 10 seconds
 continue

 # Process the job
 self._process_timelapse_job(job)

 except Exception as e:
 self.logger.error(f"Processing loop error: {e}")
 time.sleep(30.0)

 def _process_timelapse_job(self, job: TimelapseJob) -> None:
 """Process a single timelapse job"""
 try:
 # Download original video from S3
 self.logger.info(f"Downloading {job.original_s3_key} for timelapse processing")

 self.s3_client.download_file(
 config.aws.bucket_name,
 job.original_s3_key,
 job.original_local_path
 )

 # Create timelapse
 result = self.processor.create_timelapse(job)

 # Update statistics
 self.total_processed += 1
 self.total_processing_time += result.processing_time_seconds

 if result.success:
 self.successful_conversions += 1
 self.total_space_saved += (result.original_size_bytes - result.timelapse_size_bytes)

 # Upload timelapse to S3
 self.logger.info(f"Uploading timelapse {job.timelapse_s3_key}")

 self.s3_client.upload_file(
 job.timelapse_local_path,
 config.aws.bucket_name,
 job.timelapse_s3_key,
 ExtraArgs={
 'Metadata': {
 'original_s3_key': job.original_s3_key,
 'compression_ratio': str(result.compression_ratio),
 'original_size': str(result.original_size_bytes),
 'timelapse_size': str(result.timelapse_size_bytes),
 'processing_time': str(result.processing_time_seconds),
 'created_at': datetime.now(timezone.utc).isoformat()
 }
 }
 )

 # Delete original video from S3 (replaced by timelapse)
 self.s3_client.delete_object(
 Bucket=config.aws.bucket_name,
 Key=job.original_s3_key
 )

 self.logger.info(
 f"Timelapse conversion completed: {job.original_s3_key} -> {job.timelapse_s3_key} "
 f"({result.compression_ratio:.1f}% space saved)"
 )
 else:
 self.failed_conversions += 1
 self.logger.error(f"Timelapse conversion failed: {result.error_message}")

 # Cleanup local files
 for path in [job.original_local_path, job.timelapse_local_path]:
 try:
 if Path(path).exists():
 Path(path).unlink()
 except Exception as e:
 self.logger.warning(f"Failed to cleanup {path}: {e}")

 except Exception as e:
 self.failed_conversions += 1
 self.logger.error(f"Timelapse job processing failed: {e}")

 def get_statistics(self) -> Dict:
 """Get service statistics"""
 return {
 'running': self.running,
 'queue_size': len(self.processing_queue),
 'total_processed': self.total_processed,
 'successful_conversions': self.successful_conversions,
 'failed_conversions': self.failed_conversions,
 'success_rate': (self.successful_conversions / self.total_processed * 100) if self.total_processed > 0 else 0,
 'total_space_saved_gb': self.total_space_saved / (1024 * 1024 * 1024),
 'total_processing_time_hours': self.total_processing_time / 3600,
 'average_processing_time_minutes': (self.total_processing_time / self.total_processed / 60) if self.total_processed > 0 else 0
 }

# Global timelapse service instance
timelapse_service = TimelapseService()