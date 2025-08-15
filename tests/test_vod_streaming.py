#!/usr/bin/env python3
"""
VOD Streaming API Tests
Tests the Video-on-Demand streaming API endpoints
"""

import os
import sys
import requests
import json
import time
import subprocess
import threading
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class VODStreamingTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8087"
        self.server_process = None
        
    def start_test_server(self):
        """Start VOD server for testing"""
        print("Starting VOD server for testing...")
        
        try:
            # Start server in background
            self.server_process = subprocess.Popen([
                sys.executable,
                str(Path(__file__).parent.parent / "src" / "nvr_vod_server.py"),
                "--host", "127.0.0.1",
                "--port", "8087"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            time.sleep(3)
            
            # Test if server is responding
            try:
                response = requests.get(f"{self.base_url}/api/v1/health", timeout=5)
                if response.status_code == 200:
                    print("PASS VOD server started successfully")
                    return True
                else:
                    print(f"FAIL Server not responding: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                print(f"FAIL Could not connect to server: {e}")
                return False
                
        except Exception as e:
            print(f"FAIL Failed to start server: {e}")
            return False
    
    def stop_test_server(self):
        """Stop the test server"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("VOD server stopped")
            except Exception as e:
                print(f"Error stopping server: {e}")
                try:
                    self.server_process.kill()
                except:
                    pass
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        print("\nTesting health endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print("PASS Health endpoint working")
                print(f"   Status: {data.get('status')}")
                print(f"   Version: {data.get('version')}")
                return True
            else:
                print(f"FAIL Health endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"FAIL Health endpoint error: {e}")
            return False
    
    def test_cameras_endpoint(self):
        """Test cameras endpoint"""
        print("\nTesting cameras endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/cameras", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print("PASS Cameras endpoint working")
                print(f"   Total cameras: {data.get('total', 0)}")
                return True
            else:
                print(f"FAIL Cameras endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"FAIL Cameras endpoint error: {e}")
            return False
    
    def test_video_search_endpoint(self):
        """Test video search endpoint"""
        print("\nTesting video search endpoint...")
        
        try:
            params = {
                'camera_id': 'amcrest_001',
                'limit': 10
            }
            response = requests.get(f"{self.base_url}/api/v1/videos/search", 
                                  params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print("PASS Video search endpoint working")
                print(f"   Videos found: {len(data.get('videos', []))}")
                return True
            else:
                print(f"FAIL Video search endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"FAIL Video search endpoint error: {e}")
            return False
    
    def test_system_status_endpoint(self):
        """Test system status endpoint"""
        print("\nTesting system status endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/system/status", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print("PASS System status endpoint working")
                print(f"   Status: {data.get('status')}")
                return True
            else:
                print(f"FAIL System status endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"FAIL System status endpoint error: {e}")
            return False
    
    def test_streaming_url_endpoint(self):
        """Test streaming URL endpoint"""
        print("\nTesting streaming URL endpoint...")
        
        try:
            video_path = "test/sample_video.mp4"
            response = requests.get(f"{self.base_url}/api/v1/videos/{video_path}/stream", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print("PASS Streaming URL endpoint working")
                print(f"   Streaming URL generated: {bool(data.get('streaming_url'))}")
                return True
            else:
                print(f"FAIL Streaming URL endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"FAIL Streaming URL endpoint error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all VOD streaming tests"""
        print("VOD Streaming API Tests")
        print("=" * 40)
        
        # Start server
        if not self.start_test_server():
            print("FAIL Cannot start test server")
            return False
        
        try:
            results = {}
            
            # Run all tests
            results['health'] = self.test_health_endpoint()
            results['cameras'] = self.test_cameras_endpoint()
            results['video_search'] = self.test_video_search_endpoint()
            results['system_status'] = self.test_system_status_endpoint()
            results['streaming_url'] = self.test_streaming_url_endpoint()
            
            # Summary
            passed = sum(1 for v in results.values() if v)
            total = len(results)
            
            print(f"\n" + "=" * 40)
            print(f"VOD API Test Results:")
            print(f"   PASS Passed: {passed}/{total}")
            print(f"   FAIL Failed: {total - passed}")
            
            if passed == total:
                print("\nPASS All VOD API tests passed!")
                return True
            else:
                print(f"\nFAIL {total - passed} tests failed")
                return False
                
        finally:
            self.stop_test_server()
    
    def run_quick_test(self):
        """Run quick VOD API test"""
        print("Quick VOD API Test")
        print("=" * 30)
        
        # Start server
        if not self.start_test_server():
            return False
        
        try:
            # Just test health endpoint
            success = self.test_health_endpoint()
            
            if success:
                print("\nPASS Quick VOD API test passed")
            else:
                print("\nFAIL Quick VOD API test failed")
            
            return success
            
        finally:
            self.stop_test_server()

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VOD Streaming API Tests')
    parser.add_argument('--quick', action='store_true', help='Run quick test only')
    
    args = parser.parse_args()
    
    tester = VODStreamingTester()
    
    try:
        if args.quick:
            success = tester.run_quick_test()
        else:
            success = tester.run_all_tests()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        tester.stop_test_server()
        sys.exit(1)
    except Exception as e:
        print(f"Test error: {e}")
        tester.stop_test_server()
        sys.exit(1)

if __name__ == "__main__":
    main()