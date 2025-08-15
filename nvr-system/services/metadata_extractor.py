"""
Video Metadata Extraction Service - Optimized for Amcrest NVR recordings
Extracts metadata from video files with specialized support for .dav containers and NVR filename patterns
"""

import cv2
import json
import logging
import numpy as np
import subprocess
import re
import threading
import time
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import hashlib

from ..config.nvr_config import config

logger = logging.getLogger(__name__)

# Amcrest filename patterns
AMCREST_PATTERNS = [
 re.compile(r"ch(?P<ch>\d{1,2})[_-]?(?P<ts>\d{14})"), # ch1_20250814123045
 re.compile(r"(?P<cam>[^_]+)_(?P<ts>\d{8}T\d{6})Z?"), # camera_YYYYMMDDTHHMMSSZ
 re.compile(r"(?P<ts>\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})"), # YYYYMMDD_HHMMSS
]

@dataclass
class MotionEvent:
 """Represents a motion detection event"""
 timestamp: datetime
 confidence: float
 bbox: Tuple[int, int, int, int] # x, y, width, height
 frame_number: int

@dataclass
class VideoMetadata:
 """Complete video metadata"""
 # File information
 file_path: str
 file_size: int
 file_hash: str

 # Video properties
 duration: float
 width: int
 height: int
 fps: float
 frame_count: int
 codec: str
 bitrate: int

 # Timestamps
 start_timestamp: datetime
 end_timestamp: datetime

 # Camera information
 camera_id: str
 site_id: str

 # Motion detection
 motion_events: List[MotionEvent]
 motion_percentage: float

 # Quality metrics
 average_brightness: float
 average_contrast: float
 sharpness_score: float

 # Processing metadata
 processed_at: datetime
 processing_duration: float

class MetadataExtractor:
 """Extracts comprehensive metadata from video files with Amcrest optimization"""

 def __init__(self):
 self.logger = logging.getLogger(__name__)
 self.current_clip_start = None

 # Motion detection setup
 self.motion_detector = cv2.createBackgroundSubtractorMOG2(
 detectShadows=True,
 varThreshold=16,
 history=500
 )

 def extract_metadata(self, video_path: str, camera_id: str, site_id: str) -> VideoMetadata:
 """Extract complete metadata from video file"""
 start_time = datetime.now()
 self.logger.info(f"Starting metadata extraction for {video_path}")

 try:
 # Basic file information
 file_path = Path(video_path)
 file_size = file_path.stat().st_size
 file_hash = self._calculate_file_hash(video_path)

 # Detect .dav files and use ffprobe for media info
 if file_path.suffix.lower() == '.dav':
 media_info = self._probe_media_ffprobe(video_path)
 else:
 media_info = self._probe_media_opencv(video_path)

 width, height, fps, frame_count, duration, codec = media_info

 # Calculate bitrate
 bitrate = int((file_size * 8) / duration) if duration > 0 else 0

 # Extract timestamps using optimized Amcrest patterns
 start_timestamp, end_timestamp = self._extract_timestamps(video_path, duration)
 self.current_clip_start = start_timestamp

 # Analyze frames for motion and quality (only if enabled)
 camera_config = config.get_camera(camera_id)
 if camera_config and hasattr(camera_config, 'motion_detection_enabled') and camera_config.motion_detection_enabled:
 motion_events, motion_percentage, avg_brightness, avg_contrast, sharpness = self._analyze_frames(
 video_path, fps, start_timestamp
 )
 else:
 # Skip motion analysis for faster processing
 motion_events = []
 motion_percentage = 0.0
 avg_brightness = avg_contrast = sharpness = 0.0

 # Create metadata object
 metadata = VideoMetadata(
 file_path=str(file_path),
 file_size=file_size,
 file_hash=file_hash,
 duration=duration,
 width=width,
 height=height,
 fps=fps,
 frame_count=frame_count,
 codec=codec,
 bitrate=bitrate,
 start_timestamp=start_timestamp,
 end_timestamp=end_timestamp,
 camera_id=camera_id,
 site_id=site_id,
 motion_events=motion_events,
 motion_percentage=motion_percentage,
 average_brightness=avg_brightness,
 average_contrast=avg_contrast,
 sharpness_score=sharpness,
 processed_at=datetime.now(timezone.utc),
 processing_duration=(datetime.now() - start_time).total_seconds()
 )

 self.logger.info(f"Metadata extraction completed for {video_path} in {metadata.processing_duration:.2f}s")
 return metadata

 except Exception as e:
 self.logger.error(f"Failed to extract metadata from {video_path}: {e}")
 raise

 def _probe_media_ffprobe(self, path: str) -> Tuple[int, int, float, int, float, str]:
 """Use ffprobe to get media information (for .dav files)"""
 try:
 cmd = [
 "ffprobe", "-v", "error", "-print_format", "json",
 "-show_streams", "-show_format", path
 ]
 result = subprocess.run(cmd, capture_output=True, text=True, check=True)
 info = json.loads(result.stdout)

 # Find video stream
 video_stream = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
 if not video_stream:
 raise ValueError("No video stream found")

 width = int(video_stream["width"])
 height = int(video_stream["height"])

 # Parse frame rate
 fps_str = video_stream.get("r_frame_rate", "0/1")
 if "/" in fps_str:
 num, den = map(int, fps_str.split("/"))
 fps = num / den if den != 0 else 0.0
 else:
 fps = float(fps_str)

 # Get duration and frame count
 duration = float(video_stream.get("duration") or info["format"].get("duration") or 0.0)
 frame_count = int(float(video_stream.get("nb_frames") or 0))
 if frame_count == 0 and fps > 0:
 frame_count = int(duration * fps)

 codec = video_stream.get("codec_name", "unknown")

 return width, height, fps, frame_count, duration, codec

 except Exception as e:
 self.logger.warning(f"ffprobe failed for {path}: {e}")
 return self._probe_media_opencv(path)

 def _probe_media_opencv(self, path: str) -> Tuple[int, int, float, int, float, str]:
 """Use OpenCV to get media information (fallback)"""
 cap = cv2.VideoCapture(path)
 if not cap.isOpened():
 raise ValueError(f"Cannot open video file: {path}")

 try:
 width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
 height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 fps = cap.get(cv2.CAP_PROP_FPS)
 frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
 duration = frame_count / fps if fps > 0 else 0

 # Get codec information
 fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
 codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

 return width, height, fps, frame_count, duration, codec

 finally:
 cap.release()

 def _calculate_file_hash(self, file_path: str) -> str:
 """Calculate SHA-256 hash of file"""
 hash_sha256 = hashlib.sha256()
 with open(file_path, "rb") as f:
 for chunk in iter(lambda: f.read(4096), b""):
 hash_sha256.update(chunk)
 return hash_sha256.hexdigest()

 def _extract_timestamps(self, video_path: str, duration: float) -> Tuple[datetime, datetime]:
 """Extract start and end timestamps using optimized Amcrest patterns"""
 file_path = Path(video_path)
 filename = file_path.stem
 start = None

 # Try Amcrest patterns first
 for pattern in AMCREST_PATTERNS:
 match = pattern.search(filename)
 if match:
 ts = match.group("ts") if "ts" in match.groupdict() else None
 if ts:
 try:
 if "T" in ts:
 # Format: YYYYMMDDTHHMMSS
 start = datetime.strptime(ts, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
 else:
 # Format: YYYYMMDDHHMMSS
 start = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
 break
 except ValueError:
 continue

 # Fallback to file modification time
 if start is None:
 mtime = file_path.stat().st_mtime
 start = datetime.fromtimestamp(mtime, tz=timezone.utc)

 # Calculate end time properly (fix the original bug)
 end = start + timedelta(seconds=int(duration))

 return start, end

 def _analyze_frames(self, video_path: str, fps: float, start_timestamp: datetime) -> Tuple[List[MotionEvent], float, float, float, float]:
 """Analyze video frames for motion detection and quality metrics"""
 motion_events = []
 brightness_values = []
 contrast_values = []
 sharpness_values = []

 # Open video for analysis
 cap = cv2.VideoCapture(video_path)
 if not cap.isOpened():
 return [], 0.0, 0.0, 0.0, 0.0

 try:
 frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

 # Sample frames (analyze every Nth frame for performance)
 sample_interval = max(1, int(fps)) # Sample once per second
 motion_frames = 0
 total_sampled_frames = 0

 for frame_idx in range(0, frame_count, sample_interval):
 cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
 ret, frame = cap.read()

 if not ret:
 break

 total_sampled_frames += 1
 timestamp_seconds = frame_idx / fps

 # Convert to grayscale for analysis
 gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

 # Motion detection
 motion_mask = self.motion_detector.apply(frame)
 motion_pixels = cv2.countNonZero(motion_mask)
 total_pixels = motion_mask.shape[0] * motion_mask.shape[1]
 motion_ratio = motion_pixels / total_pixels

 if motion_ratio > 0.01: # 1% threshold for motion
 motion_frames += 1

 # Find motion bounding box
 contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
 if contours:
 # Get largest contour
 largest_contour = max(contours, key=cv2.contourArea)
 x, y, w, h = cv2.boundingRect(largest_contour)

 # Base motion event timestamps on clip start, not "now"
 event_time = self.current_clip_start + timedelta(seconds=timestamp_seconds)
 motion_events.append(MotionEvent(
 timestamp=event_time,
 confidence=min(motion_ratio * 100, 100.0),
 bbox=(x, y, w, h),
 frame_number=frame_idx
 ))

 # Quality metrics
 brightness = np.mean(gray)
 contrast = np.std(gray)
 sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

 brightness_values.append(brightness)
 contrast_values.append(contrast)
 sharpness_values.append(sharpness)

 # Calculate averages
 motion_percentage = (motion_frames / total_sampled_frames * 100) if total_sampled_frames > 0 else 0
 avg_brightness = np.mean(brightness_values) if brightness_values else 0
 avg_contrast = np.mean(contrast_values) if contrast_values else 0
 avg_sharpness = np.mean(sharpness_values) if sharpness_values else 0

 return motion_events, motion_percentage, avg_brightness, avg_contrast, avg_sharpness

 finally:
 cap.release()

 def save_metadata(self, metadata: VideoMetadata, output_path: str) -> None:
 """Save metadata to JSON file"""
 try:
 # Convert to dictionary with proper serialization
 metadata_dict = asdict(metadata)

 # Convert datetime objects to ISO strings
 metadata_dict['start_timestamp'] = metadata.start_timestamp.isoformat()
 metadata_dict['end_timestamp'] = metadata.end_timestamp.isoformat()
 metadata_dict['processed_at'] = metadata.processed_at.isoformat()

 # Convert motion events
 metadata_dict['motion_events'] = [
 {
 'timestamp': event.timestamp.isoformat(),
 'confidence': event.confidence,
 'bbox': event.bbox,
 'frame_number': event.frame_number
 }
 for event in metadata.motion_events
 ]

 # Ensure output directory exists
 os.makedirs(os.path.dirname(output_path), exist_ok=True)

 with open(output_path, 'w') as f:
 json.dump(metadata_dict, f, indent=2)

 self.logger.info(f"Metadata saved to {output_path}")

 except Exception as e:
 self.logger.error(f"Failed to save metadata to {output_path}: {e}")
 raise

 def generate_s3_metadata_headers(self, metadata: VideoMetadata) -> Dict[str, str]:
 """Generate S3 metadata headers for Lambda indexer compatibility"""
 return {
 'site_id': metadata.site_id,
 'camera_id': metadata.camera_id,
 'start_ts': metadata.start_timestamp.isoformat(),
 'end_ts': metadata.end_timestamp.isoformat(),
 'duration_sec': str(int(metadata.duration)),
 'width': str(metadata.width),
 'height': str(metadata.height),
 'fps': str(metadata.fps),
 'codec': metadata.codec,
 'bitrate': str(metadata.bitrate),
 'motion_percentage': str(metadata.motion_percentage),
 'motion_events': str(len(metadata.motion_events))
 }

class MetadataExtractorService:
 """Service for extracting metadata from video files"""

 def __init__(self):
 self.logger = logging.getLogger(__name__)
 self.extractor = MetadataExtractor()
 self.processing_queue = []
 self.processing_thread: Optional[threading.Thread] = None
 self.running = False

 # Statistics
 self.processed_files = 0
 self.processing_errors = 0
 self.total_processing_time = 0.0

 def start(self) -> None:
 """Start the metadata extraction service"""
 if self.running:
 self.logger.warning("Metadata extractor already running")
 return

 self.running = True
 self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
 self.processing_thread.start()

 self.logger.info("Metadata extraction service started")

 def stop(self) -> None:
 """Stop the metadata extraction service"""
 self.running = False

 if self.processing_thread and self.processing_thread.is_alive():
 self.processing_thread.join(timeout=10.0)

 self.logger.info("Metadata extraction service stopped")

 def queue_file_for_processing(self, video_path: str, camera_id: str, site_id: str) -> None:
 """Add a video file to the processing queue"""
 task = (video_path, camera_id, site_id)
 if task not in self.processing_queue:
 self.processing_queue.append(task)
 self.logger.debug(f"Queued file for metadata extraction: {video_path}")

 def _processing_loop(self) -> None:
 """Main processing loop"""
 while self.running:
 try:
 if not self.processing_queue:
 time.sleep(1.0)
 continue

 # Get next file to process
 video_path, camera_id, site_id = self.processing_queue.pop(0)

 # Process the file
 start_time = time.time()
 metadata = self.extractor.extract_metadata(video_path, camera_id, site_id)
 processing_time = time.time() - start_time

 if metadata:
 # Save metadata to JSON file
 self._save_metadata(metadata)
 self.processed_files += 1
 self.total_processing_time += processing_time

 self.logger.info(f"Extracted metadata for {video_path}")
 else:
 self.processing_errors += 1
 self.logger.error(f"Failed to extract metadata for {video_path}")

 except Exception as e:
 self.logger.error(f"Processing loop error: {e}")
 self.processing_errors += 1
 time.sleep(1.0)

 def _save_metadata(self, metadata: VideoMetadata) -> None:
 """Save metadata to JSON file"""
 try:
 video_path = Path(metadata.file_path)
 metadata_path = video_path.with_suffix('.metadata.json')

 self.extractor.save_metadata(metadata, str(metadata_path))

 except Exception as e:
 self.logger.error(f"Failed to save metadata: {e}")

 def get_statistics(self) -> Dict:
 """Get service statistics"""
 return {
 'running': self.running,
 'queue_size': len(self.processing_queue),
 'processed_files': self.processed_files,
 'processing_errors': self.processing_errors,
 'total_processing_time': self.total_processing_time,
 'average_processing_time': (
 self.total_processing_time / self.processed_files
 if self.processed_files > 0 else 0
 )
 }

# Global metadata extractor service instance
metadata_extractor_service = MetadataExtractorService()