#!/usr/bin/env python3
"""
Production Readiness Test Suite
Comprehensive tests to ensure system is ready for real camera deployment
"""

import os
import sys
import time
import subprocess
import requests
import json
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionReadinessTester:
 def __init__(self):
 self.base_path = Path(__file__).parent.parent
 self.test_results = {}

 def test_environment_configuration(self):
 """Test environment configuration completeness"""
 logger.info(" Testing Environment Configuration...")

 required_vars = [
 'AWS_REGION',
 'AWS_S3_BUCKET',
 'AWS_ACCESS_KEY_ID',
 'AWS_SECRET_ACCESS_KEY'
 ]

 optional_vars = [
 'NVR_HOST',
 'NVR_STORAGE_PATH',
 'CLOUDFRONT_DOMAIN',
 'CAMERA_amcrest_001_IP'
 ]

 missing_required = []
 missing_optional = []

 # Check required variables
 for var in required_vars:
 if not os.getenv(var):
 missing_required.append(var)
 else:
 logger.info(f" PASS {var}: Configured")

 # Check optional variables
 for var in optional_vars:
 if not os.getenv(var):
 missing_optional.append(var)
 else:
 logger.info(f" PASS {var}: Configured")

 if missing_required:
 logger.error(f" FAIL Missing required variables: {', '.join(missing_required)}")
 return False

 if missing_optional:
 logger.warning(f" WARNING Missing optional variables: {', '.join(missing_optional)}")

 logger.info(" PASS Environment configuration acceptable")
 return True

 def test_aws_connectivity_comprehensive(self):
 """Comprehensive AWS connectivity test"""
 logger.info(" Testing AWS Connectivity...")

 try:
 result = subprocess.run([
 sys.executable,
 str(self.base_path / "tests" / "test_aws_setup.py")
 ], capture_output=True, text=True, timeout=60)

 if result.returncode == 0:
 logger.info(" PASS AWS connectivity tests passed")

 # Check for specific capabilities
 output = result.stdout
 if "S3 access successful" in output:
 logger.info(" PASS S3 access confirmed")
 if "upload successful" in output:
 logger.info(" PASS S3 upload capability confirmed")
 if "DynamoDB access successful" in output:
 logger.info(" PASS DynamoDB access confirmed")

 return True
 else:
 logger.error(f" FAIL AWS connectivity failed: {result.stderr}")
 return False

 except subprocess.TimeoutExpired:
 logger.error(" ⏰ AWS connectivity test timed out")
 return False
 except Exception as e:
 logger.error(f" FAIL AWS connectivity test error: {e}")
 return False

 def test_system_components_startup(self):
 """Test all system components can start properly"""
 logger.info(" Testing System Components Startup...")

 components_tested = 0
 components_passed = 0

 # Test VOD Server startup
 logger.info(" Testing VOD Server...")
 try:
 vod_process = subprocess.Popen([
 sys.executable,
 str(self.base_path / "src" / "nvr_vod_server.py"),
 "--port", "8083"
 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

 time.sleep(3) # Allow startup time

 if vod_process.poll() is None:
 # Test if server responds
 try:
 response = requests.get("http://localhost:8083/api/v1/health", timeout=5)
 if response.status_code == 200:
 logger.info(" PASS VOD Server: Started and responding")
 components_passed += 1
 else:
 logger.error(f" FAIL VOD Server: Bad response {response.status_code}")
 except requests.exceptions.RequestException:
 logger.error(" FAIL VOD Server: Not responding to requests")

 vod_process.terminate()
 vod_process.wait(timeout=5)
 else:
 logger.error(" FAIL VOD Server: Failed to start")

 components_tested += 1

 except Exception as e:
 logger.error(f" FAIL VOD Server test error: {e}")
 components_tested += 1

 # Test System Manager
 logger.info(" Testing System Manager...")
 try:
 result = subprocess.run([
 sys.executable,
 str(self.base_path / "src" / "nvr_system_manager.py"),
 "--help"
 ], capture_output=True, text=True, timeout=10)

 if result.returncode == 0 and "NVR System Manager" in result.stdout:
 logger.info(" PASS System Manager: Available and functional")
 components_passed += 1
 else:
 logger.error(" FAIL System Manager: Not working properly")

 components_tested += 1

 except Exception as e:
 logger.error(f" FAIL System Manager test error: {e}")
 components_tested += 1

 # Test Connection Tester
 logger.info(" Testing Connection Tester...")
 try:
 result = subprocess.run([
 sys.executable,
 str(self.base_path / "tools" / "nvr_connection_tester.py"),
 "--help"
 ], capture_output=True, text=True, timeout=10)

 if result.returncode == 0 and "NVR Connection Tester" in result.stdout:
 logger.info(" PASS Connection Tester: Available and functional")
 components_passed += 1
 else:
 logger.error(" FAIL Connection Tester: Not working properly")

 components_tested += 1

 except Exception as e:
 logger.error(f" FAIL Connection Tester test error: {e}")
 components_tested += 1

 success_rate = components_passed / components_tested if components_tested > 0 else 0
 logger.info(f" Component startup success: {success_rate:.1%} ({components_passed}/{components_tested})")

 return success_rate >= 0.8 # 80% success rate required

 def test_api_endpoints_comprehensive(self):
 """Comprehensive API endpoint testing"""
 logger.info(" Testing API Endpoints...")

 # Start VOD server for testing
 vod_process = None
 try:
 vod_process = subprocess.Popen([
 sys.executable,
 str(self.base_path / "src" / "nvr_vod_server.py"),
 "--port", "8084"
 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

 time.sleep(3) # Allow startup

 if vod_process.poll() is not None:
 logger.error(" FAIL Could not start VOD server for API testing")
 return False

 base_url = "http://localhost:8084/api/v1"
 endpoints_tested = 0
 endpoints_passed = 0

 # Test each endpoint
 test_endpoints = [
 ("/health", "Health check"),
 ("/cameras", "Camera listing"),
 ("/sites", "Site listing"),
 ("/videos/search", "Video search"),
 ("/system/status", "System status")
 ]

 for endpoint, description in test_endpoints:
 logger.info(f" Testing {description}...")
 try:
 response = requests.get(f"{base_url}{endpoint}", timeout=5)

 if response.status_code == 200:
 # Validate JSON response
 data = response.json()
 if isinstance(data, dict):
 logger.info(f" PASS {description}: Working")
 endpoints_passed += 1
 else:
 logger.error(f" FAIL {description}: Invalid JSON response")
 else:
 logger.error(f" FAIL {description}: HTTP {response.status_code}")

 endpoints_tested += 1

 except requests.exceptions.RequestException as e:
 logger.error(f" FAIL {description}: Request failed - {e}")
 endpoints_tested += 1
 except json.JSONDecodeError:
 logger.error(f" FAIL {description}: Invalid JSON response")
 endpoints_tested += 1

 success_rate = endpoints_passed / endpoints_tested if endpoints_tested > 0 else 0
 logger.info(f" API endpoint success: {success_rate:.1%} ({endpoints_passed}/{endpoints_tested})")

 return success_rate >= 0.8 # 80% success rate required

 except Exception as e:
 logger.error(f" FAIL API testing error: {e}")
 return False
 finally:
 if vod_process:
 vod_process.terminate()
 try:
 vod_process.wait(timeout=5)
 except subprocess.TimeoutExpired:
 vod_process.kill()

 def test_error_handling(self):
 """Test system error handling capabilities"""
 logger.info("🛡️ Testing Error Handling...")

 error_scenarios_passed = 0
 error_scenarios_tested = 0

 # Test invalid API requests
 logger.info(" Testing invalid API requests...")
 try:
 vod_process = subprocess.Popen([
 sys.executable,
 str(self.base_path / "src" / "nvr_vod_server.py"),
 "--port", "8085"
 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

 time.sleep(3)

 if vod_process.poll() is None:
 # Test invalid endpoints
 invalid_tests = [
 ("/api/v1/nonexistent", 404),
 ("/api/v1/videos/invalid_key/stream", 404),
 ("/invalid/path", 404)
 ]

 for endpoint, expected_status in invalid_tests:
 try:
 response = requests.get(f"http://localhost:8085{endpoint}", timeout=5)
 if response.status_code == expected_status:
 logger.info(f" PASS Error handling: {endpoint} -> {expected_status}")
 error_scenarios_passed += 1
 else:
 logger.warning(f" WARNING Error handling: {endpoint} -> {response.status_code} (expected {expected_status})")

 error_scenarios_tested += 1

 except requests.exceptions.RequestException:
 logger.warning(f" WARNING Could not test error scenario: {endpoint}")
 error_scenarios_tested += 1

 vod_process.terminate()
 vod_process.wait(timeout=5)

 except Exception as e:
 logger.error(f" FAIL Error handling test failed: {e}")

 # Test missing configuration handling
 logger.info(" Testing missing configuration handling...")
 try:
 # Test with minimal environment
 env = os.environ.copy()
 for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']:
 env.pop(key, None)

 result = subprocess.run([
 sys.executable,
 str(self.base_path / "tests" / "test_aws_setup.py"),
 "--quick"
 ], env=env, capture_output=True, text=True, timeout=30)

 # Should fail gracefully, not crash
 if result.returncode != 0 and "No AWS credentials found" in result.stdout:
 logger.info(" PASS Missing credentials handled gracefully")
 error_scenarios_passed += 1
 else:
 logger.warning(" WARNING Missing credentials not handled properly")

 error_scenarios_tested += 1

 except Exception as e:
 logger.error(f" FAIL Configuration error test failed: {e}")
 error_scenarios_tested += 1

 success_rate = error_scenarios_passed / error_scenarios_tested if error_scenarios_tested > 0 else 0
 logger.info(f" Error handling success: {success_rate:.1%} ({error_scenarios_passed}/{error_scenarios_tested})")

 return success_rate >= 0.7 # 70% success rate for error handling

 def test_performance_baseline(self):
 """Test basic performance characteristics"""
 logger.info(" Testing Performance Baseline...")

 performance_tests_passed = 0
 performance_tests_total = 0

 # Test API response times
 logger.info(" Testing API response times...")
 try:
 vod_process = subprocess.Popen([
 sys.executable,
 str(self.base_path / "src" / "nvr_vod_server.py"),
 "--port", "8086"
 ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

 time.sleep(3)

 if vod_process.poll() is None:
 endpoints = [
 "/api/v1/health",
 "/api/v1/cameras",
 "/api/v1/videos/search"
 ]

 for endpoint in endpoints:
 response_times = []

 # Test 5 requests to get average
 for _ in range(5):
 try:
 start_time = time.time()
 response = requests.get(f"http://localhost:8086{endpoint}", timeout=5)
 end_time = time.time()

 if response.status_code == 200:
 response_times.append(end_time - start_time)
 except:
 pass

 if response_times:
 avg_time = sum(response_times) / len(response_times)
 if avg_time < 1.0: # Less than 1 second
 logger.info(f" PASS {endpoint}: {avg_time:.3f}s average")
 performance_tests_passed += 1
 else:
 logger.warning(f" WARNING {endpoint}: {avg_time:.3f}s (slow)")
 else:
 logger.error(f" FAIL {endpoint}: No successful responses")

 performance_tests_total += 1

 vod_process.terminate()
 vod_process.wait(timeout=5)

 except Exception as e:
 logger.error(f" FAIL Performance test error: {e}")

 success_rate = performance_tests_passed / performance_tests_total if performance_tests_total > 0 else 0
 logger.info(f" Performance baseline: {success_rate:.1%} ({performance_tests_passed}/{performance_tests_total})")

 return success_rate >= 0.8 # 80% of endpoints should be fast

 def run_production_readiness_test(self):
 """Run complete production readiness test suite"""
 logger.info(" Starting Production Readiness Test Suite")
 logger.info("=" * 70)

 test_categories = [
 ("Environment Configuration", self.test_environment_configuration),
 ("AWS Connectivity", self.test_aws_connectivity_comprehensive),
 ("System Components", self.test_system_components_startup),
 ("API Endpoints", self.test_api_endpoints_comprehensive),
 ("Error Handling", self.test_error_handling),
 ("Performance Baseline", self.test_performance_baseline)
 ]

 results = {}

 for category_name, test_func in test_categories:
 logger.info(f"\n🔍 Testing: {category_name}")
 try:
 results[category_name] = test_func()
 status = "PASS PASS" if results[category_name] else "FAIL FAIL"
 logger.info(f" {status}: {category_name}")
 except Exception as e:
 logger.error(f" FAIL ERROR: {category_name} - {e}")
 results[category_name] = False

 # Calculate overall readiness
 passed = sum(1 for result in results.values() if result)
 total = len(results)
 readiness_score = passed / total

 logger.info("\n" + "=" * 70)
 logger.info(" PRODUCTION READINESS RESULTS:")
 logger.info("=" * 70)

 for category, result in results.items():
 status = "PASS READY" if result else "FAIL NEEDS WORK"
 logger.info(f" {status} {category}")

 logger.info(f"\n Overall Readiness Score: {readiness_score:.1%} ({passed}/{total})")

 # Provide readiness assessment
 if readiness_score >= 0.9:
 logger.info("\n SYSTEM IS PRODUCTION READY!")
 logger.info(" PASS All critical systems tested and working")
 logger.info(" PASS Ready for real camera deployment")
 logger.info(" PASS Suitable for production use")
 elif readiness_score >= 0.75:
 logger.info("\nWARNING SYSTEM IS MOSTLY READY")
 logger.info(" PASS Core functionality working")
 logger.info(" WARNING Some components may need attention")
 logger.info(" Review failed tests before production")
 elif readiness_score >= 0.5:
 logger.info("\n SYSTEM NEEDS WORK")
 logger.info(" WARNING Multiple components failing")
 logger.info(" Address issues before camera deployment")
 logger.info(" Not recommended for production yet")
 else:
 logger.info("\nFAIL SYSTEM NOT READY")
 logger.info(" FAIL Major issues detected")
 logger.info(" Significant work needed")
 logger.info(" Do not deploy to production")

 logger.info("\n Next Steps:")
 if readiness_score >= 0.9:
 logger.info(" 1. Deploy to production environment")
 logger.info(" 2. Connect real cameras")
 logger.info(" 3. Monitor system performance")
 else:
 logger.info(" 1. Fix failing test categories")
 logger.info(" 2. Re-run production readiness tests")
 logger.info(" 3. Verify all systems before deployment")

 return readiness_score >= 0.75

def main():
 """Main test runner"""
 import argparse

 parser = argparse.ArgumentParser(description='Test Production Readiness of NVR System')
 parser.add_argument('--category', help='Test specific category only')

 args = parser.parse_args()

 tester = ProductionReadinessTester()

 if args.category:
 # Test specific category
 category_map = {
 'env': tester.test_environment_configuration,
 'aws': tester.test_aws_connectivity_comprehensive,
 'components': tester.test_system_components_startup,
 'api': tester.test_api_endpoints_comprehensive,
 'errors': tester.test_error_handling,
 'performance': tester.test_performance_baseline
 }

 if args.category in category_map:
 logger.info(f"🔍 Testing category: {args.category}")
 success = category_map[args.category]()
 return 0 if success else 1
 else:
 logger.error(f"FAIL Unknown category: {args.category}")
 logger.info(f"Available categories: {', '.join(category_map.keys())}")
 return 1
 else:
 # Run full test suite
 success = tester.run_production_readiness_test()
 return 0 if success else 1

if __name__ == '__main__':
 sys.exit(main())