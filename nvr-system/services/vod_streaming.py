"""
Video-on-Demand (VOD) Streaming Service
Provides global video streaming capabilities using AWS CloudFront and S3
"""

import boto3
import json
import logging
import time
import hashlib
import hmac
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from urllib.parse import quote_plus
import requests
from botocore.exceptions import ClientError

from ..config.nvr_config import config

@dataclass
class VideoInfo:
 """Video information for streaming"""
 s3_key: str
 camera_id: str
 site_id: str
 start_timestamp: datetime
 end_timestamp: datetime
 duration_seconds: float
 file_size: int
 width: int
 height: int
 fps: float
 codec: str
 motion_percentage: float
 motion_events: int
 is_timelapse: bool = False

@dataclass
class StreamingURL:
 """Streaming URL with metadata"""
 url: str
 expires_at: datetime
 video_info: VideoInfo
 adaptive_urls: Optional[Dict[str, str]] = None # Quality -> URL mapping

class CloudFrontSigner:
 """Handles CloudFront signed URL generation"""

 def __init__(self, key_id: str, private_key: str):
 self.key_id = key_id
 self.private_key = private_key
 self.logger = logging.getLogger(__name__)

 def generate_signed_url(self, url: str, expires_at: datetime) -> str:
 """Generate CloudFront signed URL"""
 try:
 # Convert expiration to epoch timestamp
 expires_timestamp = int(expires_at.timestamp())

 # Create policy
 policy = {
 "Statement": [{
 "Resource": url,
 "Condition": {
 "DateLessThan": {
 "AWS:EpochTime": expires_timestamp
 }
 }
 }]
 }

 # Convert policy to JSON and encode
 policy_json = json.dumps(policy, separators=(',', ':'))
 policy_b64 = base64.b64encode(policy_json.encode()).decode()
 policy_b64 = policy_b64.replace('+', '-').replace('=', '_').replace('/', '~')

 # Create signature
 signature = hmac.new(
 self.private_key.encode(),
 policy_json.encode(),
 hashlib.sha1
 ).digest()
 signature_b64 = base64.b64encode(signature).decode()
 signature_b64 = signature_b64.replace('+', '-').replace('=', '_').replace('/', '~')

 # Build signed URL
 separator = '&' if '?' in url else '?'
 signed_url = f"{url}{separator}Expires={expires_timestamp}&Signature={signature_b64}&Key-Pair-Id={self.key_id}"

 return signed_url

 except Exception as e:
 self.logger.error(f"Failed to generate signed URL: {e}")
 return url # Return unsigned URL as fallback

class VideoTranscoder:
 """Handles video transcoding for adaptive bitrate streaming"""

 def __init__(self):
 self.logger = logging.getLogger(__name__)
 self.s3_client = None
 self.lambda_client = None

 # Initialize AWS clients
 self._initialize_aws_clients()

 def _initialize_aws_clients(self) -> None:
 """Initialize AWS clients"""
 try:
 self.s3_client = boto3.client(
 's3',
 region_name=config.aws.region,
 aws_access_key_id=config.aws.access_key_id,
 aws_secret_access_key=config.aws.secret_access_key
 )

 self.lambda_client = boto3.client(
 'lambda',
 region_name=config.aws.region,
 aws_access_key_id=config.aws.access_key_id,
 aws_secret_access_key=config.aws.secret_access_key
 )
 except Exception as e:
 self.logger.error(f"Failed to initialize AWS clients: {e}")

 def create_adaptive_streams(self, video_info: VideoInfo) -> Dict[str, str]:
 """Create adaptive bitrate streams for a video"""
 try:
 # Define quality levels based on original resolution
 quality_levels = self._get_quality_levels(video_info.width, video_info.height)

 adaptive_urls = {}

 for quality, params in quality_levels.items():
 # Check if transcoded version exists
 transcoded_key = self._get_transcoded_key(video_info.s3_key, quality)

 try:
 # Check if transcoded file exists
 self.s3_client.head_object(Bucket=config.aws.bucket_name, Key=transcoded_key)

 # Generate CloudFront URL for transcoded version
 cloudfront_url = f"https://{config.aws.cloudfront_domain}/{transcoded_key}"
 adaptive_urls[quality] = cloudfront_url

 except ClientError as e:
 if e.response['Error']['Code'] == '404':
 # Transcoded version doesn't exist, trigger transcoding
 self._trigger_transcoding(video_info.s3_key, quality, params)

 # For now, use original video
 original_url = f"https://{config.aws.cloudfront_domain}/{video_info.s3_key}"
 adaptive_urls[quality] = original_url
 else:
 raise

 return adaptive_urls

 except Exception as e:
 self.logger.error(f"Failed to create adaptive streams: {e}")
 return {}

 def _get_quality_levels(self, width: int, height: int) -> Dict[str, Dict]:
 """Get appropriate quality levels based on original resolution"""
 quality_levels = {}

 # Always include original quality
 quality_levels['original'] = {
 'width': width,
 'height': height,
 'bitrate': '4000k'
 }

 # Add lower quality levels if original is high resolution
 if height >= 1080:
 quality_levels['720p'] = {
 'width': 1280,
 'height': 720,
 'bitrate': '2500k'
 }
 quality_levels['480p'] = {
 'width': 854,
 'height': 480,
 'bitrate': '1000k'
 }
 elif height >= 720:
 quality_levels['480p'] = {
 'width': 854,
 'height': 480,
 'bitrate': '1000k'
 }

 return quality_levels

 def _get_transcoded_key(self, original_key: str, quality: str) -> str:
 """Generate S3 key for transcoded version"""
 path_parts = original_key.rsplit('.', 1)
 if len(path_parts) == 2:
 return f"{path_parts[0]}_{quality}.{path_parts[1]}"
 else:
 return f"{original_key}_{quality}"

 def _trigger_transcoding(self, s3_key: str, quality: str, params: Dict) -> None:
 """Trigger video transcoding using Lambda function"""
 try:
 # Create transcoding job payload
 payload = {
 'source_bucket': config.aws.bucket_name,
 'source_key': s3_key,
 'target_bucket': config.aws.bucket_name,
 'target_key': self._get_transcoded_key(s3_key, quality),
 'quality': quality,
 'params': params
 }

 # Invoke transcoding Lambda (if it exists)
 try:
 self.lambda_client.invoke(
 FunctionName=f"{config.aws.region}-video-transcoder",
 InvocationType='Event', # Async
 Payload=json.dumps(payload)
 )

 self.logger.info(f"Triggered transcoding for {s3_key} to {quality}")

 except ClientError as e:
 if e.response['Error']['Code'] == 'ResourceNotFoundException':
 self.logger.warning("Video transcoding Lambda function not found")
 else:
 raise

 except Exception as e:
 self.logger.error(f"Failed to trigger transcoding: {e}")

class VODStreamingService:
 """Video-on-Demand streaming service"""

 def __init__(self):
 self.logger = logging.getLogger(__name__)
 self.s3_client = None
 self.dynamodb_client = None
 self.cloudfront_signer = None
 self.transcoder = VideoTranscoder()

 # Initialize AWS clients
 self._initialize_aws_clients()

 # Cache for video metadata
 self.video_cache = {}
 self.cache_ttl = 3600 # 1 hour

 def _initialize_aws_clients(self) -> None:
 """Initialize AWS clients"""
 try:
 self.s3_client = boto3.client(
 's3',
 region_name=config.aws.region,
 aws_access_key_id=config.aws.access_key_id,
 aws_secret_access_key=config.aws.secret_access_key
 )

 self.dynamodb_client = boto3.client(
 'dynamodb',
 region_name=config.aws.region,
 aws_access_key_id=config.aws.access_key_id,
 aws_secret_access_key=config.aws.secret_access_key
 )

 # Initialize CloudFront signer if credentials are available
 # Note: In production, you'd load these from secure storage
 if hasattr(config.aws, 'cloudfront_key_id') and hasattr(config.aws, 'cloudfront_private_key'):
 self.cloudfront_signer = CloudFrontSigner(
 config.aws.cloudfront_key_id,
 config.aws.cloudfront_private_key
 )

 except Exception as e:
 self.logger.error(f"Failed to initialize AWS clients: {e}")

 def search_videos(self, camera_id: Optional[str] = None, site_id: Optional[str] = None,
 start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
 has_motion: Optional[bool] = None, limit: int = 100) -> List[VideoInfo]:
 """Search for videos based on criteria"""
 try:
 videos = []

 # Query DynamoDB for video metadata
 query_params = {
 'TableName': config.aws.dynamodb_table,
 'Limit': limit
 }

 # Build query based on parameters
 if camera_id:
 query_params['KeyConditionExpression'] = 'camera_id = :camera_id'
 query_params['ExpressionAttributeValues'] = {':camera_id': {'S': camera_id}}

 if start_date:
 query_params['KeyConditionExpression'] += ' AND start_ts >= :start_date'
 query_params['ExpressionAttributeValues'][':start_date'] = {'S': start_date.isoformat()}

 if end_date:
 if 'KeyConditionExpression' in query_params:
 query_params['KeyConditionExpression'] += ' AND start_ts <= :end_date'
 else:
 query_params['KeyConditionExpression'] = 'start_ts <= :end_date'
 query_params['ExpressionAttributeValues'][':end_date'] = {'S': end_date.isoformat()}

 response = self.dynamodb_client.query(**query_params)
 else:
 # Scan if no camera_id specified (less efficient)
 filter_expressions = []
 expression_values = {}

 if site_id:
 filter_expressions.append('site_id = :site_id')
 expression_values[':site_id'] = {'S': site_id}

 if start_date:
 filter_expressions.append('start_ts >= :start_date')
 expression_values[':start_date'] = {'S': start_date.isoformat()}

 if end_date:
 filter_expressions.append('start_ts <= :end_date')
 expression_values[':end_date'] = {'S': end_date.isoformat()}

 if has_motion is not None:
 if has_motion:
 filter_expressions.append('motion_percentage > :motion_threshold')
 expression_values[':motion_threshold'] = {'N': '0'}
 else:
 filter_expressions.append('motion_percentage = :no_motion')
 expression_values[':no_motion'] = {'N': '0'}

 if filter_expressions:
 query_params['FilterExpression'] = ' AND '.join(filter_expressions)
 query_params['ExpressionAttributeValues'] = expression_values

 response = self.dynamodb_client.scan(**query_params)

 # Convert DynamoDB items to VideoInfo objects
 for item in response.get('Items', []):
 video_info = self._dynamodb_item_to_video_info(item)
 if video_info:
 videos.append(video_info)

 # Sort by start timestamp (newest first)
 videos.sort(key=lambda v: v.start_timestamp, reverse=True)

 return videos

 except Exception as e:
 self.logger.error(f"Video search failed: {e}")
 return []

 def get_streaming_url(self, s3_key: str, expires_in_hours: int = 24,
 quality: Optional[str] = None) -> Optional[StreamingURL]:
 """Get streaming URL for a video"""
 try:
 # Get video info from cache or DynamoDB
 video_info = self._get_video_info(s3_key)
 if not video_info:
 return None

 # Calculate expiration time
 expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

 # Generate base CloudFront URL
 if quality and quality != 'original':
 # Use transcoded version if available
 transcoded_key = self.transcoder._get_transcoded_key(s3_key, quality)
 base_url = f"https://{config.aws.cloudfront_domain}/{transcoded_key}"
 else:
 base_url = f"https://{config.aws.cloudfront_domain}/{s3_key}"

 # Generate signed URL if signer is available
 if self.cloudfront_signer:
 signed_url = self.cloudfront_signer.generate_signed_url(base_url, expires_at)
 else:
 signed_url = base_url

 # Create adaptive streaming URLs
 adaptive_urls = self.transcoder.create_adaptive_streams(video_info)

 # Sign adaptive URLs if signer is available
 if self.cloudfront_signer and adaptive_urls:
 signed_adaptive_urls = {}
 for quality_level, url in adaptive_urls.items():
 signed_adaptive_urls[quality_level] = self.cloudfront_signer.generate_signed_url(url, expires_at)
 adaptive_urls = signed_adaptive_urls

 return StreamingURL(
 url=signed_url,
 expires_at=expires_at,
 video_info=video_info,
 adaptive_urls=adaptive_urls
 )

 except Exception as e:
 self.logger.error(f"Failed to generate streaming URL for {s3_key}: {e}")
 return None

 def get_video_thumbnail(self, s3_key: str) -> Optional[str]:
 """Get thumbnail URL for a video"""
 try:
 # Generate thumbnail S3 key
 thumbnail_key = s3_key.replace('.mp4', '_thumbnail.jpg')

 # Check if thumbnail exists
 try:
 self.s3_client.head_object(Bucket=config.aws.bucket_name, Key=thumbnail_key)

 # Generate CloudFront URL for thumbnail
 thumbnail_url = f"https://{config.aws.cloudfront_domain}/{thumbnail_key}"

 # Sign URL if signer is available
 if self.cloudfront_signer:
 expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
 thumbnail_url = self.cloudfront_signer.generate_signed_url(thumbnail_url, expires_at)

 return thumbnail_url

 except ClientError as e:
 if e.response['Error']['Code'] == '404':
 # Thumbnail doesn't exist, could trigger generation here
 return None
 else:
 raise

 except Exception as e:
 self.logger.error(f"Failed to get thumbnail for {s3_key}: {e}")
 return None

 def create_playlist(self, video_infos: List[VideoInfo], expires_in_hours: int = 24) -> Dict[str, Any]:
 """Create a playlist of videos for continuous playback"""
 try:
 playlist = {
 'id': hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
 'created_at': datetime.now(timezone.utc).isoformat(),
 'expires_at': (datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).isoformat(),
 'videos': []
 }

 for video_info in video_infos:
 streaming_url = self.get_streaming_url(video_info.s3_key, expires_in_hours)
 if streaming_url:
 playlist['videos'].append({
 'id': hashlib.md5(video_info.s3_key.encode()).hexdigest()[:8],
 'title': f"{video_info.camera_id} - {video_info.start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
 'url': streaming_url.url,
 'adaptive_urls': streaming_url.adaptive_urls,
 'duration': video_info.duration_seconds,
 'thumbnail': self.get_video_thumbnail(video_info.s3_key),
 'metadata': {
 'camera_id': video_info.camera_id,
 'site_id': video_info.site_id,
 'start_timestamp': video_info.start_timestamp.isoformat(),
 'motion_percentage': video_info.motion_percentage,
 'is_timelapse': video_info.is_timelapse
 }
 })

 return playlist

 except Exception as e:
 self.logger.error(f"Failed to create playlist: {e}")
 return {}

 def _get_video_info(self, s3_key: str) -> Optional[VideoInfo]:
 """Get video information from cache or DynamoDB"""
 # Check cache first
 cache_key = f"video_info:{s3_key}"
 if cache_key in self.video_cache:
 cached_data, cached_time = self.video_cache[cache_key]
 if time.time() - cached_time < self.cache_ttl:
 return cached_data

 try:
 # Parse camera_id from S3 key
 key_parts = s3_key.split('/')
 if len(key_parts) < 3:
 return None

 site_id = key_parts[1]
 camera_id = key_parts[2]

 # Query DynamoDB for video metadata
 # Note: This is a simplified query - in practice you'd need to handle
 # the fact that we don't know the exact start_ts
 response = self.dynamodb_client.query(
 TableName=config.aws.dynamodb_table,
 KeyConditionExpression='camera_id = :camera_id',
 FilterExpression='s3_key = :s3_key',
 ExpressionAttributeValues={
 ':camera_id': {'S': camera_id},
 ':s3_key': {'S': s3_key}
 },
 Limit=1
 )

 if response['Items']:
 video_info = self._dynamodb_item_to_video_info(response['Items'][0])

 # Cache the result
 self.video_cache[cache_key] = (video_info, time.time())

 return video_info

 return None

 except Exception as e:
 self.logger.error(f"Failed to get video info for {s3_key}: {e}")
 return None

 def _dynamodb_item_to_video_info(self, item: Dict) -> Optional[VideoInfo]:
 """Convert DynamoDB item to VideoInfo object"""
 try:
 return VideoInfo(
 s3_key=item['s3_key']['S'],
 camera_id=item['camera_id']['S'],
 site_id=item['site_id']['S'],
 start_timestamp=datetime.fromisoformat(item['start_ts']['S']),
 end_timestamp=datetime.fromisoformat(item.get('end_ts', {}).get('S', item['start_ts']['S'])),
 duration_seconds=float(item.get('duration_sec', {}).get('N', '0')),
 file_size=int(item.get('size', {}).get('N', '0')),
 width=int(item.get('width', {}).get('N', '0')),
 height=int(item.get('height', {}).get('N', '0')),
 fps=float(item.get('fps', {}).get('N', '0')),
 codec=item.get('codec', {}).get('S', 'unknown'),
 motion_percentage=float(item.get('motion_percentage', {}).get('N', '0')),
 motion_events=int(item.get('motion_events', {}).get('N', '0')),
 is_timelapse='timelapse' in item['s3_key']['S']
 )
 except Exception as e:
 self.logger.error(f"Failed to convert DynamoDB item to VideoInfo: {e}")
 return None

 def get_statistics(self) -> Dict:
 """Get service statistics"""
 try:
 # Get total video count from DynamoDB
 response = self.dynamodb_client.describe_table(TableName=config.aws.dynamodb_table)
 total_videos = response['Table']['ItemCount']

 # Get cache statistics
 cache_size = len(self.video_cache)

 return {
 'total_videos': total_videos,
 'cache_size': cache_size,
 'cache_ttl_seconds': self.cache_ttl,
 'cloudfront_domain': config.aws.cloudfront_domain,
 'signed_urls_enabled': self.cloudfront_signer is not None
 }

 except Exception as e:
 self.logger.error(f"Failed to get statistics: {e}")
 return {}

# Global VOD streaming service instance
vod_streaming_service = VODStreamingService()