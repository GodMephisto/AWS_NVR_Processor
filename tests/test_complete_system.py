#!/usr/bin/env python3
"""
Complete System Integration Test
Tests the entire NVR pipeline from video files to streaming
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class CompleteSystemTester:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.test_videos_path = self.base_path / "test_videos"
        
    def setup_test_environment(self):
        """Set up test environment"""
        print("🔧 Setting up test environment...")
        
        # Create test videos if they don't exist
        if not self.test_videos_path.exists():
            print("   Creating test videos...")
            subprocess.run([
                sys.executable, 
                str(self.base_path / "tests" / "create_test_videos.py")
            ])
        else:
            print("   ✅ Test videos already exist")
        
        # Check for .env file
        env_file = self.base_path / ".env"
        if not env_file.exists():
            print("   ⚠️  No .env file found - create one with AWS credentials")
            return False
        else:
            print("   ✅ Environment file found")
        
        return True
    
    def test_metadata_extraction(self):
        """Test metadata extraction from test videos"""
        print("\n📊 Testing Metadata Extraction...")
        
        try:
            from nvr_system.services.metadata_extractor import MetadataExtractor
            
            extractor = MetadataExtractor()
            
            # Find a test video file
            test_files = list(self.test_videos_path.rglob("*.dav"))
            if not test_files:
                print("   ❌ No test video files found")
                return False
            
            test_file = test_files[0]
            print(f"   Testing with: {test_file.name}")
            
            # Extract metadata
            metadata = extractor.extract_metadata(str(test_file))
            
            if metadata:
                print(f"   ✅ Extracted metadata:")
                print(f"      Camera: {metadata.camera_id}")
                print(f"      Site: {metadata.site_id}")
                print(f"      Timestamp: {metadata.start_timestamp}")
                print(f"      Duration: {metadata.duration_seconds}s")
                return True
            else:
                print("   ❌ Failed to extract metadata")
                return False
                
        except Exception as e:
            print(f"   ❌ Metadata extraction error: {e}")
            return False
    
    def test_cloud_sync(self):
        """Test cloud synchronization"""
        print("\n☁️  Testing Cloud Sync...")
        
        try:
            # Run cloud sync on test videos
            result = subprocess.run([
                sys.executable, 
                str(self.base_path / "nvr-system" / "services" / "cloud_sync.py"),
                "--source", str(self.test_videos_path),
                "--dry-run"  # Don't actually upload in test
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("   ✅ Cloud sync dry-run successful")
                print("   📤 Files would be uploaded to S3")
                return True
            else:
                print(f"   ❌ Cloud sync failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ⏰ Cloud sync test timed out")
            return False
        except Exception as e:
            print(f"   ❌ Cloud sync error: {e}")
            return False
    
    def test_vod_api_startup(self):
        """Test VOD API startup"""
        print("\n🌐 Testing VOD API Startup...")
        
        try:
            # Start VOD API in background
            api_process = subprocess.Popen([
                sys.executable, 
                str(self.base_path / "src" / "nvr_vod_server.py")
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment for startup
            time.sleep(3)
            
            # Check if process is still running
            if api_process.poll() is None:
                print("   ✅ VOD API started successfully")
                
                # Test basic connectivity
                import requests
                try:
                    response = requests.get("http://localhost:8080/api/v1/health", timeout=5)
                    if response.status_code == 200:
                        print("   ✅ API health check passed")
                        api_process.terminate()
                        return True
                    else:
                        print(f"   ❌ API health check failed: {response.status_code}")
                        api_process.terminate()
                        return False
                except requests.exceptions.RequestException as e:
                    print(f"   ❌ Cannot connect to API: {e}")
                    api_process.terminate()
                    return False
            else:
                stdout, stderr = api_process.communicate()
                print(f"   ❌ VOD API failed to start: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"   ❌ VOD API test error: {e}")
            return False
    
    def test_aws_connectivity(self):
        """Test AWS connectivity"""
        print("\n🔗 Testing AWS Connectivity...")
        
        try:
            result = subprocess.run([
                sys.executable, 
                str(self.base_path / "tests" / "test_aws_setup.py"),
                "--quick"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("   ✅ AWS connectivity test passed")
                return True
            else:
                print(f"   ❌ AWS connectivity failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ⏰ AWS connectivity test timed out")
            return False
        except Exception as e:
            print(f"   ❌ AWS connectivity error: {e}")
            return False
    
    def run_integration_test(self):
        """Run complete integration test"""
        print("🚀 Complete System Integration Test")
        print("=" * 50)
        
        results = {}
        
        # Setup
        if not self.setup_test_environment():
            print("❌ Test environment setup failed")
            return False
        
        # Component tests
        results['metadata'] = self.test_metadata_extraction()
        results['cloud_sync'] = self.test_cloud_sync()
        results['vod_api'] = self.test_vod_api_startup()
        results['aws_connectivity'] = self.test_aws_connectivity()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Integration Test Results:")
        
        passed = sum(1 for v in results.values() if v is True)
        failed = sum(1 for v in results.values() if v is False)
        
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        
        if failed == 0:
            print("\n🎉 All integration tests passed!")
            print("   Your NVR system is ready for deployment!")
        else:
            print(f"\n⚠️  {failed} tests failed. Check configuration and try again.")
        
        print("\n🚀 Next Steps:")
        print("1. Deploy Lambda functions to AWS")
        print("2. Upload real video files")
        print("3. Start VOD API for streaming")
        print("4. Access videos via web interface")
        
        return failed == 0

def main():
    """Main test runner"""
    tester = CompleteSystemTester()
    success = tester.run_integration_test()
    
    if success:
        print("\n✨ System is ready for production!")
    else:
        print("\n🔧 Fix the issues above and run again")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())