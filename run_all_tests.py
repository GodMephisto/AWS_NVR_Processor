#!/usr/bin/env python3
"""
Complete NVR System Test Runner
Runs all test suites to validate system readiness
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime

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
        logger.info(f"Running: {description}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Run the test
            result = subprocess.run([
                sys.executable,
                str(self.base_path / test_script)
            ], capture_output=True, text=True, timeout=120)
            
            duration = time.time() - start_time
            
            # Check if test passed
            success = result.returncode == 0
            
            if success:
                logger.info(f"PASS {description} - PASSED ({duration:.1f}s)")
            else:
                logger.error(f"FAIL {description} - FAILED ({duration:.1f}s)")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr[:500]}...")
            
            # Store results
            self.test_results[test_name] = {
                'success': success,
                'duration': duration,
                'description': description,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
            return success
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"FAIL {description} - TIMEOUT ({duration:.1f}s)")
            self.test_results[test_name] = {
                'success': False,
                'duration': duration,
                'description': description,
                'error': 'Test timed out'
            }
            return False
        except Exception as e:
            logger.error(f"ERROR {description} - ERROR: {e}")
            self.test_results[test_name] = {
                'success': False,
                'duration': time.time() - start_time,
                'description': description,
                'error': str(e)
            }
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        logger.info("Starting Complete NVR System Test Suite")
        logger.info("This will validate your system is ready for real camera footage")
        
        # Define test suites
        test_suites = [
            ('aws_setup', 'tests/test_aws_setup.py', 'AWS Connectivity and Configuration'),
            ('vod_streaming', 'tests/test_vod_streaming.py', 'Video-on-Demand API'),
            ('complete_system', 'tests/test_complete_system.py', 'Complete System Integration'),
            ('production_readiness', 'tests/test_production_readiness.py', 'Production Readiness'),
        ]
        
        logger.info(f"\nTest Plan: {len(test_suites)} test suites")
        for i, (name, script, desc) in enumerate(test_suites, 1):
            logger.info(f"   {i}. {desc}")
        
        # Run all tests
        start_time = time.time()
        
        for test_name, test_script, description in test_suites:
            # Check if test file exists
            test_file = self.base_path / test_script
            if not test_file.exists():
                logger.warning(f"SKIP {description} - Test file not found: {test_script}")
                self.test_results[test_name] = {
                    'success': None,
                    'duration': 0,
                    'description': description,
                    'error': 'Test file not found'
                }
                continue
            
            self.run_test_suite(test_name, test_script, description)
        
        total_duration = time.time() - start_time
        
        # Generate final report
        self.generate_final_report(total_duration)
    
    def generate_final_report(self, total_duration):
        """Generate comprehensive final report"""
        logger.info("\n" + "="*80)
        logger.info("FINAL TEST REPORT - NVR SYSTEM READINESS")
        logger.info("="*80)
        
        # Calculate statistics
        passed_tests = sum(1 for result in self.test_results.values() if result['success'] is True)
        failed_tests = sum(1 for result in self.test_results.values() if result['success'] is False)
        skipped_tests = sum(1 for result in self.test_results.values() if result['success'] is None)
        total_tests = len(self.test_results)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        logger.info(f"Overall Results:")
        logger.info(f"   Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1%})")
        logger.info(f"   Tests Failed: {failed_tests}")
        logger.info(f"   Tests Skipped: {skipped_tests}")
        logger.info(f"   Total Duration: {total_duration:.1f} seconds")
        
        # Individual test results
        logger.info(f"\nIndividual Test Results:")
        for test_name, result in self.test_results.items():
            if result['success'] is True:
                status = "PASS"
            elif result['success'] is False:
                status = "FAIL"
            else:
                status = "SKIP"
            
            duration = result['duration']
            description = result['description']
            logger.info(f"   {status} {description} ({duration:.1f}s)")
        
        # System readiness assessment
        logger.info(f"\nSystem Readiness Assessment:")
        
        if success_rate >= 0.9:
            logger.info("   EXCELLENT - System is fully ready for production!")
            logger.info("   All critical systems validated")
            logger.info("   Ready for real camera deployment")
            logger.info("   Suitable for immediate production use")
            
            logger.info(f"\nDeployment Recommendations:")
            logger.info("   1. Connect your Amcrest cameras")
            logger.info("   2. Run: python tools/nvr_connection_tester.py --auto-discover")
            logger.info("   3. Start system: python src/nvr_system_manager.py --start-all")
            logger.info("   4. Monitor performance for first 24 hours")
            
        elif success_rate >= 0.8:
            logger.info("   GOOD - System is ready with minor considerations")
            logger.info("   Core functionality validated")
            logger.info("   Some non-critical tests failed")
            logger.info("   Safe for production deployment")
            
            logger.info(f"\nPre-Deployment Checklist:")
            logger.info("   1. Review failed tests (non-critical)")
            logger.info("   2. Test with one camera first")
            logger.info("   3. Monitor system closely during initial deployment")
            
        elif success_rate >= 0.6:
            logger.info("   CAUTION - System has issues that should be addressed")
            logger.info("   Multiple test failures detected")
            logger.info("   Recommend fixing issues before production")
            logger.info("   Limited production deployment only")
            
            logger.info(f"\nRequired Actions:")
            logger.info("   1. Fix failing test categories")
            logger.info("   2. Re-run test suite")
            logger.info("   3. Start with single camera deployment")
            
        else:
            logger.info("   NOT READY - System has significant issues")
            logger.info("   Multiple critical failures")
            logger.info("   Substantial work needed")
            logger.info("   Do NOT deploy to production")
            
        # Show failed tests details
        failed_tests = [name for name, result in self.test_results.items() if result['success'] is False]
        if failed_tests:
            logger.info(f"\nFailed Tests Details:")
            for test_name in failed_tests:
                result = self.test_results[test_name]
                logger.info(f"   {test_name}: {result.get('error', 'Unknown error')}")
        
        # Next steps
        logger.info(f"\nImmediate Next Steps:")
        if success_rate >= 0.8:
            logger.info("   1. System validated - ready for camera deployment")
            logger.info("   2. Await Thursday hardware delivery")
            logger.info("   3. Connect cameras using NVR_CONNECTION_GUIDE.md")
            logger.info("   4. Start production system")
        else:
            logger.info("   1. Fix failing test categories")
            logger.info("   2. Review error messages above")
            logger.info("   3. Re-run tests: python run_all_tests.py")
            logger.info("   4. Seek help if issues persist")
        
        # Save detailed report
        self.save_detailed_report()
        
        logger.info(f"\nDetailed report saved to: test_report.txt")
        logger.info("="*80)
    
    def save_detailed_report(self):
        """Save detailed test report to file"""
        report_file = self.base_path / "test_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("NVR System Test Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            for test_name, result in self.test_results.items():
                f.write(f"Test: {test_name}\n")
                f.write(f"Description: {result['description']}\n")
                f.write(f"Success: {result['success']}\n")
                f.write(f"Duration: {result['duration']:.1f}s\n")
                
                if 'stdout' in result and result['stdout']:
                    f.write(f"Output:\n{result['stdout']}\n")
                
                if 'stderr' in result and result['stderr']:
                    f.write(f"Errors:\n{result['stderr']}\n")
                
                f.write("-" * 30 + "\n")
    
    def run_quick_test(self):
        """Run quick critical tests only"""
        logger.info("Running Quick System Validation")
        logger.info("=" * 40)
        
        # Critical tests only
        critical_tests = [
            ('aws_setup', 'tests/test_aws_setup.py', 'AWS Connectivity'),
        ]
        
        passed = 0
        for test_name, test_script, description in critical_tests:
            test_file = self.base_path / test_script
            if test_file.exists():
                if self.run_test_suite(test_name, test_script, description):
                    passed += 1
            else:
                logger.warning(f"SKIP {description} - Test file not found")
        
        success = passed == len(critical_tests)
        logger.info(f"\nQuick Test Result: {'PASS' if success else 'FAIL'} ({passed}/{len(critical_tests)})")
        
        return success

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NVR System Test Runner')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.quick:
            success = runner.run_quick_test()
        else:
            runner.run_all_tests()
            # Determine success based on results
            passed = sum(1 for r in runner.test_results.values() if r['success'] is True)
            total = len(runner.test_results)
            success = passed >= (total * 0.8)  # 80% pass rate
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("\nTest run interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test runner error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()