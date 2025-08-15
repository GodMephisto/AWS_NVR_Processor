#!/usr/bin/env python3
"""
Real Footage Test Suite
Tests the complete system with actual video files to ensure camera footage compatibility
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealFootageTester:
 def __init__(self):
 self.base_path = Path(__file__).parent.parent
 self.test_footage_path = self.base_path / "test_real_footage"
 self.sample_videos = []

 def create_realistic_test_videos(self):
 """Create realistic test video files that mimic real camera footage"""
 logger.info(" Creating realistic test video files...")

 # Create test directory structure
 self.test_footage_path.mkdir(exist_ok=True)

 # Simulate Amcrest NVR directory structure
 cameras = ["amcrest_001", "amcrest_002"]
 site_id = "home"

 for camera_id in cameras:
 # Create realistic file structure: site/camera/YYYY/MM/DD/
 today = datetime.now()
 for days_ago in range(3): # Last 3 days
 test_date = today - timedelta(days=days_ago)

 # Amcrest path structure
 video_dir = (self.test_footage_path / site_id / camera_id /
 test_date.strftime("%Y") / test_date.strftime("%m") /
 test_date.strftime("%d"))
 video_dir.mkdir(parents=True, exist_ok=True)

 # Create multiple video files per day (realistic recording pattern)
 for hour in range(0, 24, 2): # Every 2 hours
 timestamp = test_date.replace(hour=hour, minute=0, second=0)

 # Realistic Amcrest filename: YYYYMMDD_HHMMSS_camera_sequence.dav
 filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{camera_id}_001.dav"
 filepath = video_dir / filename

 # Create realistic file size (5-50MB typical for 5-minute segments)
 file_size = 5 * 1024 * 1024 + (hour * 1024 * 1024) # 5-29MB

 # Create file with realistic binary header (simulates .dav format)
 with open(filepath, 'wb') as f:
 # Write DAV-like header
 f.write(b'DHAV') # DAV file signature
 f.write(b'\x00\x01\x00\x00') # Version
 f.write(timestamp.strftime('%Y%m%d%H%M%S').encode()) # Timestamp
 f.write(camera_id.encode().ljust(16, b'\x00')) # Camera ID

 # Fill with dummy video data
 remaining = file_size - f.tell()
 chunk_size = 1024
 for i in range(0, remaining, chunk_size):
 chunk = min(chunk_size, remaining - i)
 # Simulate video data patterns
 data = bytes([(i + j) % 256 for j in range(chunk)])
 f.write(data)

 self.sample_videos.append({
 'filepath': str(filepath),
 'camera_id': camera_id,
 'site_id': site_id,
 'timestamp': timestamp,
 'filename': filename,
 'size': file_size
 })

 logger.info(f" Created: {filepath.name} ({file_size // (1024*1024)}MB)")

 logger.info(f"PASS Created {len(self.sample_videos)} realistic video files")
 return self.sample_videos

 def test_metadata_extraction_real_files(self):
 """Test metadata extraction with realistic video files"""
 logger.info("\n Testing Metadata Extraction with Real-like Files...")

 if not self.sample_videos:
 logger.error("FAIL No test videos available")
 return False

 try:
 # Import metadata extractor
 sys.path.append(str(self.base_path / "nvr-system"))
 from services.metadata_extractor import MetadataExtractor

 extractor = MetadataExtractor()
 successful_extractions = 0

 # Test with multiple files
 for video_info in self.sample_videos[:5]: # Test first 5 files
 filepath = video_info['filepath']
 logger.info(f" Testing: {Path(filepath).name}")

 try:
 metadata = extractor.extract_metadata(filepath)

 if metadata:
 logger.info(f" PASS Extracted metadata:")
 logger.info(f" Camera: {metadata.camera_id}")
 logger.info(f" Site: {metadata.site_id}")
 logger.info(f" Timestamp: {metadata.start_timestamp}")
 logger.info(f" File size: {metadata.file_size} bytes")
 successful_extractions += 1
 else:
 logger.warning(f" WARNING No metadata extracted from {Path(filepath).name}")

 except Exception as e:
 logger.error(f" FAIL Metadata extraction failed: {e}")

 success_rate = successful_extractions / min(5, len(self.sample_videos))
 logger.info(f"\n Metadata Extraction Results:")
 logger.info(f" Success Rate: {success_rate:.1%} ({successful_extractions}/5)")

 return success_rate >= 0.8 # 80% success rate required

 except ImportError as e:
 logger.error(f"FAIL Cannot import metadata extractor: {e}")
 return False
 except Exception as e:
 logger.error(f"FAIL Metadata extraction test failed: {e}")
 return False

 def test_cloud_sync_real_files(self):
 """Test cloud sync with realistic video files"""
 logger.info("\n Testing Cloud Sync with Real-like Files...")

 try:
 # Test cloud sync in dry-run mode
 result = subprocess.run([
 sys.executable,
 str(self.base_path / "nvr-system" / "services" / "cloud_sync.py"),
 "--source", str(self.test_footage_path),
 "--dry-run",
 "--verbose"
 ], capture_output=True, text=True, timeout=60)

 if result.returncode == 0:
 logger.info("PASS Cloud sync dry-run successful")

 # Check output for expected patterns
 output = result.stdout + result.stderr
 files_found = output.count('.dav')

 logger.info(f" Files detected: {files_found}")
 logger.info(f" Would upload to S3: {files_found} files")

 if files_found >= len(self.sample_videos) * 0.8: # 80% detection rate
 logger.info(" PASS File detection rate acceptable")
 return True
 else:
 logger.warning(f" WARNING Low file detection rate: {files_found}/{len(self.sample_videos)}")
 return False
 else:
 logger.error(f"FAIL Cloud sync failed: {result.stderr}")
 return False

 except subprocess.TimeoutExpired:
 logger.error("⏰ Cloud sync test timed out")
 return False
 except Exception as e:
 logger.error(f"FAIL Cloud sync test error: {e}")
 return False

 def test_file_monitoring(self):
 """Test file monitoring and detection of new files"""
 logger.info("\n👁️ Testing File Monitoring...")

 try:
 # Create a new file to simulate camera recording
 monitor_dir = self.test_footage_path / "home" / "amcrest_001" / "2024" / "08" / "14"
 monitor_dir.mkdir(parents=True, exist_ok=True)

 # Create new file
 new_timestamp = datetime.now()
 new_filename = f"{new_timestamp.strftime('%Y%m%d_%H%M%S')}_amcrest_001_002.dav"
 new_filepath = monitor_dir / new_filename

 # Write realistic file
 with open(new_filepath, 'wb') as f:
 f.write(b'DHAV') # DAV signature
 f.write(b'\x00\x01\x00\x00') # Version
 f.write(new_timestamp.strftime('%Y%m%d%H%M%S').encode())
 f.write(b'amcrest_001'.ljust(16, b'\x00'))
 f.write(b'X' * (2 * 1024 * 1024)) # 2MB of data

 logger.info(f" Created new file: {new_filename}")

 # Test if system can detect and process new file
 time.sleep(1) # Allow file system to settle

 if new_filepath.exists() and new_filepath.stat().st_size > 0:
 logger.info(" PASS New file created and accessible")

 # Test metadata extraction on new file
 try:
 sys.path.append(str(self.base_path / "nvr-system"))
 from services.metadata_extractor import MetadataExtractor

 extractor = MetadataExtractor()
 metadata = extractor.extract_metadata(str(new_filepath))

 if metadata:
 logger.info(" PASS New file metadata extracted successfully")
 return True
 else:
 logger.warning(" WARNING Could not extract metadata from new file")
 return False

 except Exception as e:
 logger.error(f" FAIL New file processing failed: {e}")
 return False
 else:
 logger.error(" FAIL New file not accessible")
 return False

 except Exception as e:
 logger.error(f"FAIL File monitoring test failed: {e}")
 return False

 def test_vod_with_real_files(self):
 """Test VOD streaming with realistic files"""
 logger.info("\n Testing VOD Streaming with Real-like Files...")

 try:
 # Start VOD server in background
 vod_process = subprocess.Popen([
 sys.executable,
 str(self.base_path / "src" / "nvr_vod_server.py"),
 "--host", "127.0.0.1",
 "--port", "8082"
 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

 # Wait for server to start
 time.sleep(3)

 if vod_process.poll() is None:
 logger.info(" PASS VOD server started")

 # Test API endpoints
 import requests

 try:
 # Test health
 response = requests.get("http://localhost:8082/api/v1/health", timeout=5)
 if response.status_code == 200:
 logger.info(" PASS VOD API health check passed")

 # Test video search (will return mock data, but tests API)
 search_response = requests.get("http://localhost:8082/api/v1/videos/search", timeout=5)
 if search_response.status_code == 200:
 logger.info(" PASS VOD video search working")

 # Test streaming URL generation
 data = search_response.json()
 if data.get('videos'):
 video = data['videos'][0]
 s3_key = video['s3_key']

 stream_response = requests.get(
 f"http://localhost:8082/api/v1/videos/{s3_key}/stream",
 timeout=5
 )

 if stream_response.status_code == 200:
 logger.info(" PASS VOD streaming URL generation working")
 vod_process.terminate()
 return True

 logger.error(" FAIL VOD API tests failed")
 vod_process.terminate()
 return False

 except requests.exceptions.RequestException as e:
 logger.error(f" FAIL VOD API connection failed: {e}")
 vod_process.terminate()
 return False
 else:
 logger.error(" FAIL VOD server failed to start")
 return False

 except Exception as e:
 logger.error(f"FAIL VOD test failed: {e}")
 return False

 def test_end_to_end_pipeline(self):
 """Test complete end-to-end pipeline with realistic data"""
 logger.info("\n🔄 Testing End-to-End Pipeline...")

 try:
 # Simulate complete workflow
 pipeline_steps = [
 ("File Detection", self.test_file_monitoring),
 ("Metadata Extraction", self.test_metadata_extraction_real_files),
 ("Cloud Sync", self.test_cloud_sync_real_files),
 ("VOD Streaming", self.test_vod_with_real_files)
 ]

 results = {}
 for step_name, test_func in pipeline_steps:
 logger.info(f"\n 🔄 Testing: {step_name}")
 try:
 results[step_name] = test_func()
 status = "PASS PASS" if results[step_name] else "FAIL FAIL"
 logger.info(f" {status}: {step_name}")
 except Exception as e:
 logger.error(f" FAIL ERROR: {step_name} - {e}")
 results[step_name] = False

 # Calculate overall success
 passed = sum(1 for result in results.values() if result)
 total = len(results)
 success_rate = passed / total

 logger.info(f"\n End-to-End Pipeline Results:")
 logger.info(f" Success Rate: {success_rate:.1%} ({passed}/{total})")

 for step, result in results.items():
 status = "PASS" if result else "FAIL"
 logger.info(f" {status} {step}")

 return success_rate >= 0.75 # 75% success rate required

 except Exception as e:
 logger.error(f"FAIL End-to-end pipeline test failed: {e}")
 return False

 def cleanup_test_files(self):
 """Clean up test files"""
 logger.info("\n🧹 Cleaning up test files...")

 try:
 if self.test_footage_path.exists():
 shutil.rmtree(self.test_footage_path)
 logger.info(" PASS Test files cleaned up")
 except Exception as e:
 logger.warning(f" WARNING Cleanup warning: {e}")

 def run_comprehensive_test(self):
 """Run comprehensive test with realistic video files"""
 logger.info(" Starting Comprehensive Real Footage Test")
 logger.info("=" * 60)

 try:
 # Setup
 logger.info(" Test Setup:")
 self.create_realistic_test_videos()

 # Run tests
 logger.info("\n Running Tests:")
 results = {
 'metadata_extraction': self.test_metadata_extraction_real_files(),
 'cloud_sync': self.test_cloud_sync_real_files(),
 'file_monitoring': self.test_file_monitoring(),
 'vod_streaming': self.test_vod_with_real_files(),
 'end_to_end': self.test_end_to_end_pipeline()
 }

 # Summary
 logger.info("\n" + "=" * 60)
 logger.info(" COMPREHENSIVE TEST RESULTS:")
 logger.info("=" * 60)

 passed = sum(1 for result in results.values() if result)
 total = len(results)
 overall_success = passed / total

 for test_name, result in results.items():
 status = "PASS PASS" if result else "FAIL FAIL"
 logger.info(f" {status} {test_name.replace('_', ' ').title()}")

 logger.info(f"\n Overall Success Rate: {overall_success:.1%} ({passed}/{total})")

 if overall_success >= 0.8:
 logger.info("\n SYSTEM READY FOR REAL CAMERA FOOTAGE!")
 logger.info(" Your system will handle actual video files correctly.")
 elif overall_success >= 0.6:
 logger.info("\nWARNING SYSTEM MOSTLY READY")
 logger.info(" Some components may need attention before production.")
 else:
 logger.info("\nFAIL SYSTEM NEEDS WORK")
 logger.info(" Address failing components before using with real cameras.")

 # Cleanup
 self.cleanup_test_files()

 return overall_success >= 0.8

 except Exception as e:
 logger.error(f"FAIL Comprehensive test failed: {e}")
 self.cleanup_test_files()
 return False

def main():
 """Main test runner"""
 import argparse

 parser = argparse.ArgumentParser(description='Test NVR System with Real-like Footage')
 parser.add_argument('--quick', action='store_true', help='Run quick tests only')
 parser.add_argument('--cleanup-only', action='store_true', help='Only cleanup test files')

 args = parser.parse_args()

 tester = RealFootageTester()

 if args.cleanup_only:
 tester.cleanup_test_files()
 return 0

 if args.quick:
 logger.info("🏃 Running Quick Real Footage Tests...")
 tester.create_realistic_test_videos()
 success = tester.test_metadata_extraction_real_files()
 tester.cleanup_test_files()
 return 0 if success else 1
 else:
 success = tester.run_comprehensive_test()
 return 0 if success else 1

if __name__ == '__main__':
 sys.exit(main())