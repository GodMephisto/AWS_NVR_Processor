#!/usr/bin/env python3
"""
Simple VOD Server - Minimal version for testing
"""

from flask import Flask, jsonify
import json
from datetime import datetime, timezone

app = Flask(__name__)

# Simple mock data
mock_videos = [
 {
 'id': '20240115_080000_amcrest_001_001',
 's3_key': 'test_site/amcrest_001/2024/01/15/20240115_080000_amcrest_001_001.mp4',
 'camera_id': 'amcrest_001',
 'site_id': 'test_site',
 'start_timestamp': '2024-01-15T08:00:00Z',
 'duration_seconds': 300,
 'resolution': '1920x1080',
 'motion_percentage': 15.5,
 'is_timelapse': False
 },
 {
 'id': '20240115_140000_amcrest_002_001',
 's3_key': 'test_site/amcrest_002/2024/01/15/20240115_140000_amcrest_002_001.mp4',
 'camera_id': 'amcrest_002',
 'site_id': 'test_site',
 'start_timestamp': '2024-01-15T14:00:00Z',
 'duration_seconds': 300,
 'resolution': '1920x1080',
 'motion_percentage': 22.1,
 'is_timelapse': False
 }
]

@app.route('/api/v1/health')
def health():
 return jsonify({
 'status': 'healthy',
 'timestamp': datetime.now(timezone.utc).isoformat(),
 'version': '1.0.0'
 })

@app.route('/api/v1/cameras')
def cameras():
 return jsonify({
 'cameras': [
 {'camera_id': 'amcrest_001', 'site_id': 'test_site', 'enabled': True},
 {'camera_id': 'amcrest_002', 'site_id': 'test_site', 'enabled': True}
 ],
 'total': 2
 })

@app.route('/api/v1/videos/search')
def search_videos():
 return jsonify({
 'videos': mock_videos,
 'total': len(mock_videos)
 })

@app.route('/api/v1/system/status')
def system_status():
 return jsonify({
 'status': 'running',
 'videos_indexed': len(mock_videos),
 'cameras_active': 2
 })

@app.route('/api/v1/videos/<path:s3_key>/stream')
def get_stream(s3_key):
 # Find video
 video = None
 for v in mock_videos:
 if v['s3_key'] == s3_key:
 video = v
 break

 if not video:
 return jsonify({'error': 'Video not found'}), 404

 return jsonify({
 'url': f'https://example-cloudfront.com/videos/{s3_key}?signature=mock',
 'expires_at': '2024-01-16T08:00:00Z',
 'video_info': video
 })

if __name__ == '__main__':
 print(" Starting Simple VOD Server...")
 print(" Available at: http://localhost:8080")
 print(" Health: http://localhost:8080/api/v1/health")
 print(" Videos: http://localhost:8080/api/v1/videos/search")
 print(" Cameras: http://localhost:8080/api/v1/cameras")
 print("\n Press Ctrl+C to stop\n")

 try:
 app.run(host='127.0.0.1', port=8080, debug=False)
 except Exception as e:
 print(f"FAIL Failed to start on port 8080: {e}")
 print("🔄 Trying port 8081...")
 try:
 app.run(host='127.0.0.1', port=8081, debug=False)
 except Exception as e2:
 print(f"FAIL Failed to start on port 8081: {e2}")
 print(" Try: netstat -ano | findstr :8080 to check what's using the port")