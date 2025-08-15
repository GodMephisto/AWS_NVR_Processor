#!/usr/bin/env python3
"""
Basic NVR System for 4000H Testing
Simplified version focused on core functionality with Amcrest cameras
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Import basic configuration
from config.basic_config import config

class BasicNVRSystem:
    """Simplified NVR system for testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self) -> None:
        """Start basic NVR system"""
        try:
            self.logger.info("Starting Basic NVR System for 4000H Testing...")
            
            # Validate configuration
            config_errors = config.validate_config()
            if config_errors:
                self.logger.error("Configuration validation failed:")
                for error in config_errors:
                    self.logger.error(f"  - {error}")
                return
            
            # Test AWS connectivity if configured
            if config.aws.bucket_name:
                if config.test_aws_connectivity():
                    self.logger.info("AWS connectivity test passed")
                else:
                    self.logger.warning("AWS connectivity test failed - continuing without cloud sync")
            else:
                self.logger.info("AWS not configured - running in local-only mode")
            
            self.running = True
            
            self.logger.info("Basic NVR system started successfully")
            self.logger.info(f"Configured cameras: {len(config.cameras)}")
            
            for cam_id, camera in config.cameras.items():
                self.logger.info(f"  - {cam_id}: {camera.site_id} ({'enabled' if camera.enabled else 'disabled'})")
            
            # Simple main loop
            self._main_loop()
            
        except Exception as e:
            self.logger.error(f"Failed to start NVR system: {e}")
            self.stop()
    
    def _main_loop(self) -> None:
        """Simple main system loop"""
        last_status_time = 0
        status_interval = 60  # Print status every minute
        
        while self.running:
            try:
                current_time = time.time()
                
                # Print periodic status
                if current_time - last_status_time >= status_interval:
                    self._print_status()
                    last_status_time = current_time
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                time.sleep(10)
    
    def _print_status(self) -> None:
        """Print system status"""
        try:
            self.logger.info("=== Basic NVR System Status ===")
            self.logger.info(f"Running: {self.running}")
            self.logger.info(f"Cameras configured: {len(config.cameras)}")
            self.logger.info(f"Storage path: {config.storage.base_path}")
            
            # Check storage usage
            storage_path = Path(config.storage.base_path)
            if storage_path.exists():
                try:
                    import shutil
                    total, used, free = shutil.disk_usage(storage_path)
                    used_gb = used / (1024**3)
                    free_gb = free / (1024**3)
                    self.logger.info(f"Storage: {used_gb:.1f}GB used, {free_gb:.1f}GB free")
                except Exception:
                    pass
            
            self.logger.info("===============================")
            
        except Exception as e:
            self.logger.error(f"Failed to print status: {e}")
    
    def stop(self) -> None:
        """Stop NVR system"""
        if not self.running:
            return
        
        self.logger.info("Stopping Basic NVR system...")
        self.running = False
        self.logger.info("Basic NVR system stopped")
    
    def test_camera_connection(self, camera_id: str) -> bool:
        """Test connection to a specific camera"""
        if camera_id not in config.cameras:
            self.logger.error(f"Camera {camera_id} not found in configuration")
            return False
        
        camera = config.cameras[camera_id]
        
        try:
            import cv2
            
            self.logger.info(f"Testing connection to camera {camera_id}...")
            self.logger.info(f"RTSP URL: {camera.rtsp_url}")
            
            # Try to open RTSP stream
            cap = cv2.VideoCapture(camera.rtsp_url)
            
            if not cap.isOpened():
                self.logger.error(f"Failed to connect to camera {camera_id}")
                return False
            
            # Try to read a frame
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                height, width = frame.shape[:2]
                self.logger.info(f"Camera {camera_id} connection successful - Resolution: {width}x{height}")
                return True
            else:
                self.logger.error(f"Failed to read frame from camera {camera_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Camera connection test failed: {e}")
            return False
    
    def test_all_cameras(self) -> Dict[str, bool]:
        """Test connection to all configured cameras"""
        results = {}
        
        for camera_id in config.cameras:
            results[camera_id] = self.test_camera_connection(camera_id)
        
        return results

def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration"""
    # Create logs directory
    log_dir = Path("/opt/nvr/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "basic_nvr.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Basic NVR System for 4000H Testing")
    parser.add_argument("--config", "-c", default="/opt/nvr/config/basic_config.json",
                       help="Configuration file path")
    parser.add_argument("--log-level", "-l", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Log level")
    parser.add_argument("--test-cameras", "-t", action="store_true",
                       help="Test camera connections and exit")
    parser.add_argument("--test-aws", action="store_true",
                       help="Test AWS connectivity and exit")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Basic NVR System for 4000H Testing")
    
    try:
        # Create NVR system
        nvr_system = BasicNVRSystem()
        
        if args.test_cameras:
            logger.info("Testing camera connections...")
            results = nvr_system.test_all_cameras()
            
            logger.info("Camera test results:")
            for camera_id, success in results.items():
                status = "✓ PASS" if success else "✗ FAIL"
                logger.info(f"  {camera_id}: {status}")
            
            # Exit with error code if any camera failed
            if not all(results.values()):
                sys.exit(1)
            else:
                logger.info("All camera tests passed!")
                sys.exit(0)
        
        if args.test_aws:
            logger.info("Testing AWS connectivity...")
            # Import and run AWS test
            import subprocess
            result = subprocess.run([sys.executable, "test_aws_setup.py"], 
                                  capture_output=False)
            sys.exit(result.returncode)
        
        # Start normal operation
        nvr_system.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()