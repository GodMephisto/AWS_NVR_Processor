#!/usr/bin/env python3
"""
NVR System Test Main
Main entry point for testing NVR system components
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NVRSystemTester:
    def __init__(self):
        self.base_path = Path(__file__).parent
        
    def test_configuration(self):
        """Test system configuration"""
        logger.info("Testing system configuration...")
        
        try:
            from config.basic_config import NVRConfig
            config = NVRConfig()
            logger.info("PASS Configuration loaded successfully")
            return True
        except ImportError as e:
            logger.error(f"FAIL Configuration import error: {e}")
            return False
        except Exception as e:
            logger.error(f"FAIL Configuration error: {e}")
            return False
    
    def test_services(self):
        """Test NVR services"""
        logger.info("Testing NVR services...")
        
        services_tested = 0
        services_passed = 0
        
        # Test metadata extractor
        try:
            from services.metadata_extractor import MetadataExtractor
            extractor = MetadataExtractor()
            logger.info("PASS Metadata extractor loaded")
            services_passed += 1
        except Exception as e:
            logger.error(f"FAIL Metadata extractor error: {e}")
        services_tested += 1
        
        # Test cloud sync
        try:
            from services.cloud_sync import CloudSync
            sync = CloudSync()
            logger.info("PASS Cloud sync loaded")
            services_passed += 1
        except Exception as e:
            logger.error(f"FAIL Cloud sync error: {e}")
        services_tested += 1
        
        # Test VOD streaming
        try:
            from services.vod_streaming import VODStreamingService
            vod = VODStreamingService(None)
            logger.info("PASS VOD streaming loaded")
            services_passed += 1
        except Exception as e:
            logger.error(f"FAIL VOD streaming error: {e}")
        services_tested += 1
        
        logger.info(f"Services test: {services_passed}/{services_tested} passed")
        return services_passed == services_tested
    
    def test_api(self):
        """Test API components"""
        logger.info("Testing API components...")
        
        try:
            from api.vod_api import create_vod_api
            api = create_vod_api()
            logger.info("PASS VOD API loaded")
            return True
        except Exception as e:
            logger.error(f"FAIL VOD API error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all NVR system tests"""
        logger.info("NVR System Component Tests")
        logger.info("=" * 40)
        
        results = {}
        
        # Test configuration
        results['configuration'] = self.test_configuration()
        
        # Test services
        results['services'] = self.test_services()
        
        # Test API
        results['api'] = self.test_api()
        
        # Summary
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        logger.info("\n" + "=" * 40)
        logger.info("NVR System Test Results:")
        logger.info(f"   PASS Passed: {passed}/{total}")
        logger.info(f"   FAIL Failed: {total - passed}")
        
        if passed == total:
            logger.info("\nPASS All NVR system tests passed!")
            return True
        else:
            logger.info(f"\nFAIL {total - passed} tests failed")
            return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NVR System Tester')
    parser.add_argument('--test-cameras', action='store_true', help='Test camera connections')
    
    args = parser.parse_args()
    
    tester = NVRSystemTester()
    
    try:
        if args.test_cameras:
            logger.info("Camera testing not implemented yet")
            return True
        else:
            success = tester.run_all_tests()
            return success
    
    except Exception as e:
        logger.error(f"Test error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)