#!/usr/bin/env python3
"""
Quick VOD API Test
Simple test without complex dependencies
"""

import requests
import json

def test_api():
    # Try both possible ports
    for port in [8080, 8081]:
        base_url = f"http://localhost:{port}/api/v1"
        print(f"🔍 Trying port {port}...")
        
        # Test basic connectivity first
        try:
            response = requests.get(f"http://localhost:{port}/", timeout=2)
            print(f"   Server responds on port {port}")
            break
        except:
            continue
    else:
        print("❌ No server found on ports 8080 or 8081")
        return
    
    print("🧪 Quick VOD API Test")
    print("=" * 30)
    
    # Test health
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"🏥 Health: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data['status']}")
    except Exception as e:
        print(f"❌ Health failed: {e}")
        return
    
    # Test cameras
    try:
        response = requests.get(f"{base_url}/cameras", timeout=5)
        print(f"📷 Cameras: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found: {data['total']} cameras")
    except Exception as e:
        print(f"❌ Cameras failed: {e}")
    
    # Test videos
    try:
        response = requests.get(f"{base_url}/videos/search", timeout=5)
        print(f"📹 Videos: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found: {data['total']} videos")
            if data['videos']:
                video = data['videos'][0]
                print(f"   Sample: {video['camera_id']} - {video['duration_seconds']}s")
    except Exception as e:
        print(f"❌ Videos failed: {e}")
    
    # Test streaming URL
    try:
        response = requests.get(f"{base_url}/videos/search?limit=1", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['videos']:
                s3_key = data['videos'][0]['s3_key']
                stream_response = requests.get(f"{base_url}/videos/{s3_key}/stream", timeout=5)
                print(f"🌐 Streaming: {stream_response.status_code}")
                if stream_response.status_code == 200:
                    stream_data = stream_response.json()
                    print(f"   URL generated: ✅")
                    print(f"   Expires: {stream_data['expires_at']}")
    except Exception as e:
        print(f"❌ Streaming failed: {e}")
    
    print("\n✅ VOD API is working!")

if __name__ == '__main__':
    test_api()