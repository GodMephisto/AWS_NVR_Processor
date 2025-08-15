#!/usr/bin/env python3
"""
VOD API Server on Port 8081
Alternative port in case 8080 has issues
"""

# Import everything from the main server
from start_vod_api import app

if __name__ == '__main__':
    print("🚀 Starting VOD API Server on Port 8081...")
    print("📡 Server will be available at: http://localhost:8081")
    print("🏥 Health check: http://localhost:8081/api/v1/health")
    print("📹 Video search: http://localhost:8081/api/v1/videos/search")
    print("📷 Cameras: http://localhost:8081/api/v1/cameras")
    print("\n✨ Press Ctrl+C to stop")
    
    # Run on port 8081
    app.run(host='127.0.0.1', port=8081, debug=False, use_reloader=False)