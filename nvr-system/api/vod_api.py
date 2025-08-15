"""
VOD Streaming REST API
Provides HTTP endpoints for video search, streaming, and playlist management
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import traceback

from ..services.vod_streaming import vod_streaming_service
from ..config.nvr_config import config

# Create Flask app
app = Flask(__name__)
CORS(app) # Enable CORS for web clients

logger = logging.getLogger(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
 """Global exception handler"""
 logger.error(f"API error: {e}")
 logger.error(traceback.format_exc())
 return jsonify({
 'error': 'Internal server error',
 'message': str(e)
 }), 500

@app.route('/api/v1/videos/search', methods=['GET'])
def search_videos():
 """Search for videos based on query parameters"""
 try:
 # Parse query parameters
 camera_id = request.args.get('camera_id')
 site_id = request.args.get('site_id')

 # Parse date parameters
 start_date = None
 end_date = None

 if request.args.get('start_date'):
 start_date = datetime.fromisoformat(request.args.get('start_date'))

 if request.args.get('end_date'):
 end_date = datetime.fromisoformat(request.args.get('end_date'))

 # Parse motion filter
 has_motion = None
 if request.args.get('has_motion'):
 has_motion = request.args.get('has_motion').lower() == 'true'

 # Parse limit
 limit = min(int(request.args.get('limit', 100)), 1000) # Max 1000 results

 # Search videos
 videos = vod_streaming_service.search_videos(
 camera_id=camera_id,
 site_id=site_id,
 start_date=start_date,
 end_date=end_date,
 has_motion=has_motion,
 limit=limit
 )

 # Convert to JSON-serializable format
 video_list = []
 for video in videos:
 video_dict = {
 'id': video.s3_key.split('/')[-1].replace('.mp4', ''),
 's3_key': video.s3_key,
 'camera_id': video.camera_id,
 'site_id': video.site_id,
 'start_timestamp': video.start_timestamp.isoformat(),
 'end_timestamp': video.end_timestamp.isoformat(),
 'duration_seconds': video.duration_seconds,
 'file_size': video.file_size,
 'resolution': f"{video.width}x{video.height}",
 'fps': video.fps,
 'codec': video.codec,
 'motion_percentage': video.motion_percentage,
 'motion_events': video.motion_events,
 'is_timelapse': video.is_timelapse,
 'thumbnail_url': vod_streaming_service.get_video_thumbnail(video.s3_key)
 }
 video_list.append(video_dict)

 return jsonify({
 'videos': video_list,
 'total': len(video_list),
 'query': {
 'camera_id': camera_id,
 'site_id': site_id,
 'start_date': start_date.isoformat() if start_date else None,
 'end_date': end_date.isoformat() if end_date else None,
 'has_motion': has_motion,
 'limit': limit
 }
 })

 except Exception as e:
 logger.error(f"Video search failed: {e}")
 return jsonify({'error': str(e)}), 500

@app.route('/api/v1/videos/<path:s3_key>/stream', methods=['GET'])
def get_streaming_url(s3_key: str):
 """Get streaming URL for a specific video"""
 try:
 # Parse query parameters
 expires_in_hours = int(request.args.get('expires_in_hours', 24))
 quality = request.args.get('quality', 'original')

 # Get streaming URL
 streaming_url = vod_streaming_service.get_streaming_url(
 s3_key=s3_key,
 expires_in_hours=expires_in_hours,
 quality=quality
 )

 if not streaming_url:
 return jsonify({'error': 'Video not found'}), 404

 response_data = {
 'url': streaming_url.url,
 'expires_at': streaming_url.expires_at.isoformat(),
 'quality': quality,
 'video_info': {
 'camera_id': streaming_url.video_info.camera_id,
 'site_id': streaming_url.video_info.site_id,
 'start_timestamp': streaming_url.video_info.start_timestamp.isoformat(),
 'duration_seconds': streaming_url.video_info.duration_seconds,
 'resolution': f"{streaming_url.video_info.width}x{streaming_url.video_info.height}",
 'is_timelapse': streaming_url.video_info.is_timelapse
 }
 }

 # Add adaptive streaming URLs if available
 if streaming_url.adaptive_urls:
 response_data['adaptive_urls'] = streaming_url.adaptive_urls

 return jsonify(response_data)

 except Exception as e:
 logger.error(f"Failed to get streaming URL for {s3_key}: {e}")
 return jsonify({'error': str(e)}), 500

@app.route('/api/v1/playlists', methods=['POST'])
def create_playlist():
 """Create a playlist from a list of video S3 keys"""
 try:
 data = request.get_json()

 if not data or 'video_keys' not in data:
 return jsonify({'error': 'video_keys required'}), 400

 video_keys = data['video_keys']
 expires_in_hours = data.get('expires_in_hours', 24)

 # Get video info for each key
 video_infos = []
 for s3_key in video_keys:
 video_info = vod_streaming_service._get_video_info(s3_key)
 if video_info:
 video_infos.append(video_info)

 if not video_infos:
 return jsonify({'error': 'No valid videos found'}), 404

 # Create playlist
 playlist = vod_streaming_service.create_playlist(video_infos, expires_in_hours)

 return jsonify(playlist)

 except Exception as e:
 logger.error(f"Failed to create playlist: {e}")
 return jsonify({'error': str(e)}), 500

@app.route('/api/v1/cameras', methods=['GET'])
def list_cameras():
 """List all available cameras"""
 try:
 cameras = []

 for camera_id, camera_config in config.cameras.items():
 camera_info = {
 'camera_id': camera_id,
 'site_id': camera_config.site_id,
 'enabled': camera_config.enabled,
 'recording_enabled': camera_config.recording_enabled,
 'motion_detection_enabled': camera_config.motion_detection_enabled
 }
 cameras.append(camera_info)

 return jsonify({
 'cameras': cameras,
 'total': len(cameras)
 })

 except Exception as e:
 logger.error(f"Failed to list cameras: {e}")
 return jsonify({'error': str(e)}), 500

@app.route('/api/v1/sites', methods=['GET'])
def list_sites():
 """List all available sites"""
 try:
 sites = set()

 for camera_config in config.cameras.values():
 sites.add(camera_config.site_id)

 site_list = [{'site_id': site_id} for site_id in sorted(sites)]

 return jsonify({
 'sites': site_list,
 'total': len(site_list)
 })

 except Exception as e:
 logger.error(f"Failed to list sites: {e}")
 return jsonify({'error': str(e)}), 500

@app.route('/api/v1/system/status', methods=['GET'])
def system_status():
 """Get system status and statistics"""
 try:
 # Get VOD service statistics
 vod_stats = vod_streaming_service.get_statistics()

 status = {
 'status': 'running',
 'vod_service': vod_stats,
 'configuration': {
 'cameras': len(config.cameras),
 'aws_region': config.aws.region,
 'cloudfront_domain': config.aws.cloudfront_domain
 }
 }

 return jsonify(status)

 except Exception as e:
 logger.error(f"Failed to get system status: {e}")
 return jsonify({'error': str(e)}), 500

@app.route('/api/v1/videos/<path:s3_key>/thumbnail', methods=['GET'])
def get_video_thumbnail(s3_key: str):
 """Get thumbnail URL for a video"""
 try:
 thumbnail_url = vod_streaming_service.get_video_thumbnail(s3_key)

 if not thumbnail_url:
 return jsonify({'error': 'Thumbnail not found'}), 404

 return jsonify({
 'thumbnail_url': thumbnail_url,
 's3_key': s3_key
 })

 except Exception as e:
 logger.error(f"Failed to get thumbnail for {s3_key}: {e}")
 return jsonify({'error': str(e)}), 500

@app.route('/api/v1/health', methods=['GET'])
def health_check():
 """Health check endpoint"""
 return jsonify({
 'status': 'healthy',
 'timestamp': datetime.now(timezone.utc).isoformat(),
 'version': '1.0.0'
 })

def create_app(config_override=None):
 """Application factory"""
 if config_override:
 app.config.update(config_override)

 return app

if __name__ == '__main__':
 # Development server
 app.run(host='0.0.0.0', port=8080, debug=True)