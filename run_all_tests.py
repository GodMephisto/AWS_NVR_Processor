#!/usr/bin/env python3
"""
Complete Test Runner
Runs all tests to validate system readiness for real camera footage
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestRunner:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.test_results = {}
        
    def run_test_suite(self, test_name, test_script, description):
        """Run a test suite and capture results"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 Running: {description}")
        logger.info(f"{'='*60}")
        
        try:
            start_time = time.time()
            
            # Parse script and arguments
            script_parts = test_script.split()
            script_path = str(self.base_path / script_parts[0])
            script_args = script_parts[1:] if len(script_parts) > 1 else []
            
            cmd = [sys.executable, script_path] + script_args
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.returncode == 0
            
            self.test_results[test_name] = {
                'success': success,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'description': description
            }
            
            if success:
                logger.info(f"✅ {description} - PASSED ({duration:.1f}s)")
            else:
                logger.error(f"❌ {description} - FAILED ({duration:.1f}s)")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr[:500]}...")
            
            return success
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {description} - TIMEOUT (>5 minutes)")
            self.test_results[test_name] = {
                'success': False,
                'duration': 300,
                'stdout': '',
                'stderr': 'Test timed out',
                'description': description
            }
            return False
        except Exception as e:
            logger.error(f"❌ {description} - ERROR: {e}")
            self.test_results[test_name] = {
                'success': False,
                'duration': 0,
                'stdout': '',
                'stderr': str(e),
                'description': description
            }
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        logger.info("🚀 Starting Complete NVR System Test Suite")
        logger.info("This will validate your system is ready for real camera footage")
        
        # Define test suites in order of importance
        test_suites = [
            # Core functionality tests
            ("aws_setup", "tests/test_aws_setup.py", "AWS Connectivity & Configuration"),
            ("vod_streaming", "tests/test_vod_streaming.py --quick", "VOD API Basic Functionality"),
            
            # System integration tests
            ("production_readiness", "tests/test_production_readiness.py", "Production Readiness Assessment"),
            ("real_footage", "tests/test_with_real_footage.py", "Real Footage Simulation"),
            ("complete_system", "tests/test_complete_system.py", "End-to-End Integration"),
        ]
        
        logger.info(f"\n📋 Test Plan: {len(test_suites)} test suites")
        for i, (name, script, desc) in enumerate(test_suites, 1):
            logger.info(f"   {i}. {desc}")
        
        # Run each test suite
        passed_tests = 0
        total_tests = len(test_suites)
        
        for test_name, test_script, description in test_suites:
            success = self.run_test_suite(test_name, test_script, description)
            if success:
                passed_tests += 1
            
            # Brief pause between tests
            time.sleep(2)
        
        # Generate final report
        self.generate_final_report(passed_tests, total_tests)
        
        return passed_tests / total_tests >= 0.8  # 80% pass rate required
    
    def generate_final_report(self, passed_tests, total_tests):
        """Generate comprehensive final report"""
        logger.info("\n" + "="*80)
        logger.info("📊 FINAL TEST REPORT - NVR SYSTEM READINESS")
        logger.info("="*80)
        
        # Overall statistics
        success_rate = passed_tests / total_tests
        total_duration = sum(result['duration'] for result in self.test_results.values())
        
        logger.info(f"📈 Overall Results:")
        logger.info(f"   Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1%})")
        logger.info(f"   Total Duration: {total_duration:.1f} seconds")
        logger.info(f"   Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Individual test results
        logger.info(f"\n📋 Individual Test Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            duration = result['duration']
            description = result['description']
            logger.info(f"   {status} {description} ({duration:.1f}s)")
        
        # System readiness assessment
        logger.info(f"\n🎯 System Readiness Assessment:")
        
        if success_rate >= 0.9:
            logger.info("   🎉 EXCELLENT - System is fully ready for production!")
            logger.info("   ✅ All critical systems validated")
            logger.info("   ✅ Ready for real camera deployment")
            logger.info("   ✅ Suitable for immediate production use")
            
            logger.info(f"\n🚀 Deployment Recommendations:")
            logger.info("   1. Connect your Amcrest cameras")
            logger.info("   2. Run: python tools/nvr_connection_tester.py --auto-discover")
            logger.info("   3. Start system: python src/nvr_system_manager.py --start-all")
            logger.info("   4. Monitor performance for first 24 hours")
            
        elif success_rate >= 0.8:
            logger.info("   ✅ GOOD - System is ready with minor considerations")
            logger.info("   ✅ Core functionality validated")
            logger.info("   ⚠️  Some non-critical tests failed")
            logger.info("   ✅ Safe for production deployment")
            
            logger.info(f"\n📋 Pre-Deployment Checklist:")
            logger.info("   1. Review failed tests (non-critical)")
            logger.info("   2. Test with one camera first")
            logger.info("   3. Monitor system closely during initial deployment")
            
        elif success_rate >= 0.6:
            logger.info("   ⚠️  CAUTION - System has issues that should be addressed")
            logger.info("   ⚠️  Multiple test failures detected")
            logger.info("   🔧 Recommend fixing issues before production")
            logger.info("   📋 Limited production deployment only")
            
            logger.info(f"\n🔧 Required Actions:")
            logger.info("   1. Fix failing test categories")
            logger.info("   2. Re-run test suite")
            logger.info("   3. Start with single camera deployment")
            logger.info("   4. Extensive monitoring required")
            
        else:
            logger.info("   ❌ NOT READY - System has significant issues")
            logger.info("   ❌ Multiple critical failures")
            logger.info("   🔧 Substantial work needed")
            logger.info("   ⛔ Do NOT deploy to production")
            
            logger.info(f"\n🚨 Critical Actions Required:")
            logger.info("   1. Address all failing tests")
            logger.info("   2. Review system configuration")
            logger.info("   3. Check AWS credentials and permissions")
            logger.info("   4. Re-run complete test suite")
        
        # Failed test details
        failed_tests = [name for name, result in self.test_results.items() if not result['success']]
        if failed_tests:
            logger.info(f"\n❌ Failed Tests Details:")
            for test_name in failed_tests:
                result = self.test_results[test_name]
                logger.info(f"   • {result['description']}")
                if result['stderr']:
                    logger.info(f"     Error: {result['stderr'][:200]}...")
        
        # Next steps
        logger.info(f"\n📋 Immediate Next Steps:")
        if success_rate >= 0.8:
            logger.info("   1. ✅ System validated - ready for camera deployment")
            logger.info("   2. 📦 Await Thursday hardware delivery")
            logger.info("   3. 🔌 Connect cameras using NVR_CONNECTION_GUIDE.md")
            logger.info("   4. 🚀 Start production system")
        else:
            logger.info("   1. 🔧 Fix failing test categories")
            logger.info("   2. 📋 Review error messages above")
            logger.info("   3. 🧪 Re-run tests: python run_all_tests.py")
            logger.info("   4. 📞 Seek help if issues persist")
        
        # Save detailed report
        self.save_detailed_report()
        
        logger.info(f"\n📄 Detailed report saved to: test_report.txt")
        logger.info("="*80)
    
    def save_detailed_report(self):
        """Save detailed test report to file"""
        try:
            with open("test_report.txt", "w") as f:
                f.write("NVR SYSTEM TEST REPORT\n")
                f.write("="*50 + "\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for test_name, result in self.test_results.items():
                    f.write(f"TEST: {result['description']}\n")
                    f.write(f"Status: {'PASS' if result['success'] else 'FAIL'}\n")
                    f.write(f"Duration: {result['duration']:.1f}s\n")
                    
                    if result['stdout']:
                        f.write(f"Output:\n{result['stdout']}\n")
                    
                    if result['stderr']:
                        f.write(f"Errors:\n{result['stderr']}\n")
                    
                    f.write("-" * 50 + "\n")
                    
        except Exception as e:
            logger.warning(f"Could not save detailed report: {e}")

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Complete NVR System Test Suite')
    parser.add_argument('--quick', action='store_true', help='Run only critical tests')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.quick:
        logger.info("🏃 Running Quick Test Suite...")
        # Run only critical tests
        critical_tests = [
            ("aws_setup", "tests/test_aws_setup.py --quick", "AWS Quick Check"),
            ("vod_basic", "tests/test_vod_streaming.py --quick", "VOD Basic Check")
        ]
        
        passed = 0
        for test_name, test_script, description in critical_tests:
            if runner.run_test_suite(test_name, test_script, description):
                passed += 1
        
        success = passed == len(critical_tests)
        logger.info(f"\n🎯 Quick Test Result: {'✅ PASS' if success else '❌ FAIL'} ({passed}/{len(critical_tests)})")
        return 0 if success else 1
    else:
        # Run complete test suite
        success = runner.run_all_tests()
        return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())