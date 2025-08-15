#!/usr/bin/env python3
"""
NVR VOD Server - Production Video-on-Demand API
Provides REST API for video streaming, search, and management
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from pathlib import Path

# Add nvr-system to path for imports
sys.path.append(str(Path(__file__).parent / "nvr-system"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for web clients

# Load configuration
try:
    from config.basic_config import NVRConfig
    config = NVRConfig()
    logger.info("✅ Configuration loaded successfully")
except ImportError:
    logger.warning("⚠️  Using fallback configuration")
    # Fallback configuration
    class FallbackConfig:
        def __init__(self):
            self.cameras = {
                'amcrest_001': {
                    'site_id': os.getenv('SITE_ID', 'home'),
                    'enabled': True,
                    'recording_enabled': True,
                    'motion_detection_enabled': True
                }
            }
            self.aws = {
                'region': os.getenv('AWS_REGION', 'us-east-1'),
                'cloudfront_domain': os.getenv('CLOUDFRONT_DOMAIN', 'your-cloudfront.com'),
                's3_bucket': os.getenv('AWS_S3_BUCKET', 'your-nvr-bucket')
            }
    
    config = FallbackConfig()

# Initialize services
try:
    from services.vod_streaming import VODStreamingService
    vod_service = VODStreamingService(config)
    logger.info("✅ VOD streaming service initialized")
except ImportError:
    logger.warning("⚠️  VOD service not available - using mock responses")
    vod_service = None

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"API error: {e}")
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
        limit = min(int(request.args.get('limit', 100)), 1000)
        
        # Search videos using VOD service
        if vod_service:
            videos = vod_service.search_videos(
                camera_id=camera_id,
                site_id=site_id,
                start_date=start_date,
                end_date=end_date,
                has_motion=has_motion,
                limit=limit
            )
        else:
            # Fallback mock response
            videos = []
            logger.info("Using mock video search response")
        
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
                'thumbnail_url': f"https://{config.aws['cloudfront_domain']}/thumbnails/{video.s3_key}.jpg"
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
        
        # Get streaming URL using VOD service
        if vod_service:
            streaming_url = vod_service.get_streaming_url(
                s3_key=s3_key,
                expires_in_hours=expires_in_hours,
                quality=quality
            )
        else:
            # Fallback mock response
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            streaming_url = {
                'url': f"https://{config.aws['cloudfront_domain']}/videos/{s3_key}?expires={int(expires_at.timestamp())}&signature=production",
                'expires_at': expires_at.isoformat(),
                'quality': quality
            }
        
        if not streaming_url:
            return jsonify({'error': 'Video not found'}), 404
        
        return jsonify(streaming_url)
        
    except Exception as e:
        logger.error(f"Failed to get streaming URL for {s3_key}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/cameras', methods=['GET'])
def list_cameras():
    """List all available cameras"""
    try:
        cameras = []
        
        for camera_id, camera_config in config.cameras.items():
            camera_info = {
                'camera_id': camera_id,
                'site_id': camera_config['site_id'],
                'enabled': camera_config['enabled'],
                'recording_enabled': camera_config['recording_enabled'],
                'motion_detection_enabled': camera_config['motion_detection_enabled']
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
            sites.add(camera_config['site_id'])
        
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
        if vod_service:
            vod_stats = vod_service.get_statistics()
        else:
            vod_stats = {
                'videos_indexed': 0,
                'cameras_active': len(config.cameras),
                'last_sync': datetime.now(timezone.utc).isoformat()
            }
        
        status = {
            'status': 'running',
            'vod_service': vod_stats,
            'configuration': {
                'cameras': len(config.cameras),
                'aws_region': config.aws['region'],
                'cloudfront_domain': config.aws['cloudfront_domain'],
                's3_bucket': config.aws['s3_bucket']
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0',
        'service': 'NVR VOD API'
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information"""
    return jsonify({
        'service': 'NVR Video-on-Demand API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/v1/health',
            'cameras': '/api/v1/cameras',
            'sites': '/api/v1/sites',
            'videos': '/api/v1/videos/search',
            'streaming': '/api/v1/videos/{s3_key}/stream',
            'status': '/api/v1/system/status'
        },
        'documentation': 'https://github.com/your-repo/nvr-system'
    })

def create_app(config_override=None):
    """Application factory"""
    if config_override:
        app.config.update(config_override)
    
    return app

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='NVR VOD Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print("🚀 Starting NVR VOD Server...")
    print(f"📡 Server will be available at: http://{args.host}:{args.port}")
    print(f"🏥 Health check: http://{args.host}:{args.port}/api/v1/health")
    print(f"📹 Video search: http://{args.host}:{args.port}/api/v1/videos/search")
    print(f"📷 Cameras: http://{args.host}:{args.port}/api/v1/cameras")
    print(f"📊 System status: http://{args.host}:{args.port}/api/v1/system/status")
    print("\n✨ Press Ctrl+C to stop")
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        sys.exit(1)