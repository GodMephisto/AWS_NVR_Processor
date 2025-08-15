#!/usr/bin/env python3
"""
NVR VOD Server - Production Video-on-Demand API
Provides REST API for video streaming, search, and management
"""

import os
import sys
import json
import logging
import argparse
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
    logger.info("Configuration loaded successfully")
except ImportError:
    logger.warning("Using fallback configuration")
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
    logger.info("VOD streaming service initialized")
except ImportError:
    logger.warning("VOD service not available - using mock responses")
    vod_service = None

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"API error: {e}")
    return jsonify({
        'error': 'Internal server error',
        'message': str(e)
    }), 500

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0',
        'services': {
            'vod_service': vod_service is not None,
            'config': config is not None
        }
    })

@app.route('/api/v1/cameras', methods=['GET'])
def get_cameras():
    """Get list of configured cameras"""
    try:
        cameras = []
        for camera_id, camera_config in config.cameras.items():
            cameras.append({
                'id': camera_id,
                'site_id': camera_config.get('site_id', 'unknown'),
                'enabled': camera_config.get('enabled', False),
                'recording_enabled': camera_config.get('recording_enabled', False),
                'motion_detection_enabled': camera_config.get('motion_detection_enabled', False)
            })
        
        return jsonify({
            'cameras': cameras,
            'total': len(cameras)
        })
    except Exception as e:
        logger.error(f"Error getting cameras: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/videos/search', methods=['GET'])
def search_videos():
    """Search for videos"""
    try:
        # Get query parameters
        camera_id = request.args.get('camera_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 50))
        
        # Mock response for now
        videos = []
        for i in range(min(limit, 10)):
            videos.append({
                'id': f'video_{i}',
                'camera_id': camera_id or 'amcrest_001',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'duration': 300,
                'size': 1024000,
                'path': f'/videos/camera_{camera_id or "amcrest_001"}/video_{i}.mp4'
            })
        
        return jsonify({
            'videos': videos,
            'total': len(videos),
            'query': {
                'camera_id': camera_id,
                'start_date': start_date,
                'end_date': end_date,
                'limit': limit
            }
        })
    except Exception as e:
        logger.error(f"Error searching videos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/videos/<path:video_path>/stream', methods=['GET'])
def stream_video(video_path):
    """Get streaming URL for a video"""
    try:
        # Mock streaming URL
        streaming_url = f"https://{config.aws['cloudfront_domain']}/{video_path}"
        
        return jsonify({
            'streaming_url': streaming_url,
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            'video_path': video_path
        })
    except Exception as e:
        logger.error(f"Error getting streaming URL: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/system/status', methods=['GET'])
def system_status():
    """Get system status"""
    try:
        return jsonify({
            'status': 'running',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'uptime': 'unknown',
            'services': {
                'vod_service': 'available' if vod_service else 'unavailable',
                'config': 'loaded'
            },
            'cameras': {
                'total': len(config.cameras),
                'enabled': sum(1 for c in config.cameras.values() if c.get('enabled', False))
            }
        })
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/sites', methods=['GET'])
def get_sites():
    """Get list of sites"""
    try:
        sites = set()
        for camera_config in config.cameras.values():
            sites.add(camera_config.get('site_id', 'unknown'))
        
        return jsonify({
            'sites': list(sites),
            'total': len(sites)
        })
    except Exception as e:
        logger.error(f"Error getting sites: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='NVR VOD Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print("Starting NVR VOD Server...")
    print(f"Server will be available at: http://{args.host}:{args.port}")
    print(f"Health check: http://{args.host}:{args.port}/api/v1/health")
    print(f"Video search: http://{args.host}:{args.port}/api/v1/videos/search")
    print(f"Cameras: http://{args.host}:{args.port}/api/v1/cameras")
    print(f"System status: http://{args.host}:{args.port}/api/v1/system/status")
    print("\nPress Ctrl+C to stop")
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)