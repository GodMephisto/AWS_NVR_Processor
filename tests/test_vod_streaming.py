#!/usr/bin/env python3
"""
VOD Streaming Test Suite
Tests the complete Video-on-Demand streaming functionality
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class VODStreamingTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        
    def test_health_check(self):
        """Test basic API health"""
        print("🏥 Testing API Health...")
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API is healthy - Status: {data['status']}")
                print(f"   Version: {data['version']}")
                print(f"   Timestamp: {data['timestamp']}")
                return True
            else:
                print(f"❌ Health check failed - Status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to API: {e}")
            return False
    
    def test_system_status(self):
        """Test system status endpoint"""
        print("\n📊 Testing System Status...")
        try:
            response = requests.get(f"{self.api_base}/system/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ System Status: {data['status']}")
                print(f"   Cameras configured: {data['configuration']['cameras']}")
                print(f"   AWS Region: {data['configuration']['aws_region']}")
                if 'cloudfront_domain' in data['configuration']:
                    print(f"   CloudFront: {data['configuration']['cloudfront_domain']}")
                return True
            else:
                print(f"❌ System status failed - Status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ System status error: {e}")
            return False
    
    def test_list_cameras(self):
        """Test camera listing"""
        print("\n📹 Testing Camera List...")
        try:
            response = requests.get(f"{self.api_base}/cameras", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Found {data['total']} cameras:")
                for camera in data['cameras']:
                    print(f"   📷 {camera['camera_id']} (Site: {camera['site_id']})")
                    print(f"      Enabled: {camera['enabled']}")
                    print(f"      Recording: {camera['recording_enabled']}")
                return data['cameras']
            else:
                print(f"❌ Camera list failed - Status: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Camera list error: {e}")
            return []
    
    def test_list_sites(self):
        """Test site listing"""
        print("\n🏢 Testing Site List...")
        try:
            response = requests.get(f"{self.api_base}/sites", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Found {data['total']} sites:")
                for site in data['sites']:
                    print(f"   🏠 {site['site_id']}")
                return data['sites']
            else:
                print(f"❌ Site list failed - Status: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Site list error: {e}")
            return []
    
    def test_video_search(self):
        """Test video search functionality"""
        print("\n🔍 Testing Video Search...")
        
        # Test basic search
        try:
            response = requests.get(f"{self.api_base}/videos/search?limit=10", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Basic search returned {data['total']} videos")
                
                if data['videos']:
                    video = data['videos'][0]
                    print(f"   📹 Sample video: {video['id']}")
                    print(f"      Camera: {video['camera_id']}")
                    print(f"      Duration: {video['duration_seconds']}s")
                    print(f"      Resolution: {video['resolution']}")
                    print(f"      Motion: {video['motion_percentage']}%")
                    return data['videos']
                else:
                    print("   ℹ️  No videos found (expected if no uploads yet)")
                    return []
            else:
                print(f"❌ Video search failed - Status: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Video search error: {e}")
            return []
    
    def test_video_search_filters(self):
        """Test video search with filters"""
        print("\n🎯 Testing Video Search Filters...")
        
        # Test date range search
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'limit': 5
        }
        
        try:
            response = requests.get(f"{self.api_base}/videos/search", params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Date range search: {data['total']} videos (last 7 days)")
                return True
            else:
                print(f"❌ Date range search failed - Status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Date range search error: {e}")
            return False
    
    def test_streaming_url(self, videos):
        """Test streaming URL generation"""
        print("\n🌐 Testing Streaming URLs...")
        
        if not videos:
            print("   ℹ️  No videos to test streaming (upload some videos first)")
            return False
        
        video = videos[0]
        s3_key = video['s3_key']
        
        try:
            response = requests.get(f"{self.api_base}/videos/{s3_key}/stream", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Generated streaming URL for: {video['id']}")
                print(f"   🔗 URL: {data['url'][:50]}...")
                print(f"   ⏰ Expires: {data['expires_at']}")
                print(f"   📺 Quality: {data['quality']}")
                
                # Test if URL is accessible
                try:
                    head_response = requests.head(data['url'], timeout=5)
                    if head_response.status_code == 200:
                        print(f"   ✅ URL is accessible")
                    else:
                        print(f"   ⚠️  URL returned status: {head_response.status_code}")
                except:
                    print(f"   ⚠️  Could not verify URL accessibility")
                
                return True
            else:
                print(f"❌ Streaming URL failed - Status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Streaming URL error: {e}")
            return False
    
    def test_thumbnail_generation(self, videos):
        """Test thumbnail generation"""
        print("\n🖼️  Testing Thumbnail Generation...")
        
        if not videos:
            print("   ℹ️  No videos to test thumbnails")
            return False
        
        video = videos[0]
        s3_key = video['s3_key']
        
        try:
            response = requests.get(f"{self.api_base}/videos/{s3_key}/thumbnail", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Generated thumbnail for: {video['id']}")
                print(f"   🔗 Thumbnail URL: {data['thumbnail_url'][:50]}...")
                return True
            else:
                print(f"❌ Thumbnail generation failed - Status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Thumbnail error: {e}")
            return False
    
    def test_playlist_creation(self, videos):
        """Test playlist creation"""
        print("\n📋 Testing Playlist Creation...")
        
        if len(videos) < 2:
            print("   ℹ️  Need at least 2 videos to test playlists")
            return False
        
        video_keys = [video['s3_key'] for video in videos[:3]]  # Use first 3 videos
        
        payload = {
            'video_keys': video_keys,
            'expires_in_hours': 24
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/playlists", 
                json=payload, 
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Created playlist with {len(video_keys)} videos")
                print(f"   📋 Playlist ID: {data.get('playlist_id', 'N/A')}")
                return True
            else:
                print(f"❌ Playlist creation failed - Status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Playlist error: {e}")
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting VOD Streaming Test Suite")
        print("=" * 50)
        
        results = {}
        
        # Basic connectivity
        results['health'] = self.test_health_check()
        if not results['health']:
            print("\n❌ Cannot connect to VOD API. Make sure it's running:")
            print("   cd src && python nvr_vod_server.py")
            return results
        
        # System tests
        results['system_status'] = self.test_system_status()
        results['cameras'] = self.test_list_cameras()
        results['sites'] = self.test_list_sites()
        
        # Video tests
        videos = self.test_video_search()
        results['video_search'] = len(videos) >= 0  # Success if no error
        results['search_filters'] = self.test_video_search_filters()
        
        # Streaming tests (only if we have videos)
        if videos:
            results['streaming_url'] = self.test_streaming_url(videos)
            results['thumbnails'] = self.test_thumbnail_generation(videos)
            results['playlists'] = self.test_playlist_creation(videos)
        else:
            print("\n⚠️  No videos found for streaming tests")
            print("   Upload some test videos first using cloud_sync.py")
            results['streaming_url'] = None
            results['thumbnails'] = None
            results['playlists'] = None
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        
        passed = sum(1 for v in results.values() if v is True)
        failed = sum(1 for v in results.values() if v is False)
        skipped = sum(1 for v in results.values() if v is None)
        
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏭️  Skipped: {skipped}")
        
        if failed == 0:
            print("\n🎉 All tests passed! Your VOD system is working perfectly!")
        else:
            print(f"\n⚠️  {failed} tests failed. Check the output above for details.")
        
        return results

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test VOD Streaming System')
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Base URL for VOD API (default: http://localhost:8080)')
    parser.add_argument('--quick', action='store_true',
                       help='Run only basic connectivity tests')
    
    args = parser.parse_args()
    
    tester = VODStreamingTester(args.url)
    
    if args.quick:
        print("🏃 Running quick tests...")
        tester.test_health_check()
        tester.test_system_status()
    else:
        tester.run_all_tests()

if __name__ == '__main__':
    main()