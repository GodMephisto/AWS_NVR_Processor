#!/usr/bin/env python3
"""
NVR System Manager - Production Control Interface
Manages the complete NVR system including video processing, cloud sync, and streaming
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NVRSystemManager:
    """Manages all NVR system components"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.processes = {}
        self.running = False
        
    def start_vod_server(self, host='127.0.0.1', port=8080):
        """Start the VOD streaming server"""
        logger.info("🚀 Starting VOD streaming server...")
        
        try:
            process = subprocess.Popen([
                sys.executable,
                str(self.base_path / "nvr_vod_server.py"),
                "--host", host,
                "--port", str(port)
            ])
            
            self.processes['vod_server'] = process
            logger.info(f"✅ VOD server started on {host}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start VOD server: {e}")
            return False
    
    def start_cloud_sync(self, source_path=None):
        """Start cloud synchronization service"""
        logger.info("☁️  Starting cloud sync service...")
        
        try:
            cmd = [
                sys.executable,
                str(self.base_path / "nvr-system" / "services" / "cloud_sync.py")
            ]
            
            if source_path:
                cmd.extend(["--source", source_path])
            
            process = subprocess.Popen(cmd)
            self.processes['cloud_sync'] = process
            logger.info("✅ Cloud sync service started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start cloud sync: {e}")
            return False
    
    def start_metadata_processor(self):
        """Start metadata extraction service"""
        logger.info("📊 Starting metadata processor...")
        
        try:
            process = subprocess.Popen([
                sys.executable,
                str(self.base_path / "nvr-system" / "services" / "metadata_extractor.py")
            ])
            
            self.processes['metadata_processor'] = process
            logger.info("✅ Metadata processor started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start metadata processor: {e}")
            return False
    
    def check_aws_connectivity(self):
        """Check AWS connectivity and configuration"""
        logger.info("🔗 Checking AWS connectivity...")
        
        try:
            result = subprocess.run([
                sys.executable,
                str(self.base_path / "tests" / "test_aws_setup.py"),
                "--quick"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✅ AWS connectivity verified")
                return True
            else:
                logger.warning(f"⚠️  AWS connectivity issues: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ AWS connectivity check failed: {e}")
            return False
    
    def deploy_lambda_functions(self):
        """Deploy Lambda functions to AWS"""
        logger.info("🚀 Deploying Lambda functions...")
        
        try:
            result = subprocess.run([
                sys.executable,
                str(self.base_path / "deployment" / "deploy_to_aws.py")
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info("✅ Lambda functions deployed successfully")
                return True
            else:
                logger.error(f"❌ Lambda deployment failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lambda deployment error: {e}")
            return False
    
    def get_system_status(self):
        """Get status of all system components"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        for name, process in self.processes.items():
            if process.poll() is None:
                status['components'][name] = 'running'
            else:
                status['components'][name] = 'stopped'
        
        return status
    
    def stop_all_services(self):
        """Stop all running services"""
        logger.info("🛑 Stopping all services...")
        
        for name, process in self.processes.items():
            try:
                if process.poll() is None:
                    logger.info(f"   Stopping {name}...")
                    process.terminate()
                    process.wait(timeout=10)
                    logger.info(f"   ✅ {name} stopped")
            except subprocess.TimeoutExpired:
                logger.warning(f"   ⚠️  Force killing {name}...")
                process.kill()
            except Exception as e:
                logger.error(f"   ❌ Error stopping {name}: {e}")
        
        self.processes.clear()
        self.running = False
        logger.info("✅ All services stopped")
    
    def start_full_system(self, nvr_path=None, vod_port=8080):
        """Start the complete NVR system"""
        logger.info("🚀 Starting Complete NVR System")
        logger.info("=" * 50)
        
        self.running = True
        
        # 1. Check AWS connectivity
        if not self.check_aws_connectivity():
            logger.warning("⚠️  AWS connectivity issues - some features may not work")
        
        # 2. Start VOD server
        if not self.start_vod_server(port=vod_port):
            logger.error("❌ Failed to start VOD server")
            return False
        
        # 3. Start cloud sync (if NVR path provided)
        if nvr_path:
            if not self.start_cloud_sync(nvr_path):
                logger.warning("⚠️  Cloud sync failed to start")
        
        # 4. Start metadata processor
        if not self.start_metadata_processor():
            logger.warning("⚠️  Metadata processor failed to start")
        
        logger.info("=" * 50)
        logger.info("🎉 NVR System Started Successfully!")
        logger.info(f"📡 VOD API: http://localhost:{vod_port}")
        logger.info(f"🏥 Health Check: http://localhost:{vod_port}/api/v1/health")
        logger.info(f"📹 Video Search: http://localhost:{vod_port}/api/v1/videos/search")
        logger.info("=" * 50)
        
        return True
    
    def run_interactive_mode(self):
        """Run in interactive mode with menu"""
        while self.running:
            print("\n" + "=" * 50)
            print("🎛️  NVR System Manager")
            print("=" * 50)
            print("1. Start VOD Server")
            print("2. Start Cloud Sync")
            print("3. Check System Status")
            print("4. Deploy Lambda Functions")
            print("5. Test AWS Connectivity")
            print("6. Start Full System")
            print("7. Stop All Services")
            print("8. Exit")
            print("=" * 50)
            
            try:
                choice = input("Select option (1-8): ").strip()
                
                if choice == '1':
                    port = input("VOD Server port (default 8080): ").strip() or "8080"
                    self.start_vod_server(port=int(port))
                
                elif choice == '2':
                    nvr_path = input("NVR video path (optional): ").strip() or None
                    self.start_cloud_sync(nvr_path)
                
                elif choice == '3':
                    status = self.get_system_status()
                    print(f"\n📊 System Status ({status['timestamp']}):")
                    for component, state in status['components'].items():
                        emoji = "✅" if state == "running" else "❌"
                        print(f"   {emoji} {component}: {state}")
                
                elif choice == '4':
                    self.deploy_lambda_functions()
                
                elif choice == '5':
                    self.check_aws_connectivity()
                
                elif choice == '6':
                    nvr_path = input("NVR video path (optional): ").strip() or None
                    port = input("VOD Server port (default 8080): ").strip() or "8080"
                    self.start_full_system(nvr_path, int(port))
                
                elif choice == '7':
                    self.stop_all_services()
                
                elif choice == '8':
                    self.stop_all_services()
                    break
                
                else:
                    print("❌ Invalid option")
                    
            except KeyboardInterrupt:
                print("\n🛑 Interrupted by user")
                self.stop_all_services()
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("🛑 Shutdown signal received")
    if 'manager' in globals():
        manager.stop_all_services()
    sys.exit(0)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NVR System Manager')
    parser.add_argument('--start-all', action='store_true', help='Start all services')
    parser.add_argument('--nvr-path', help='Path to NVR video storage')
    parser.add_argument('--vod-port', type=int, default=8080, help='VOD server port')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    global manager
    manager = NVRSystemManager()
    
    try:
        if args.start_all:
            success = manager.start_full_system(args.nvr_path, args.vod_port)
            if success:
                # Keep running until interrupted
                while manager.running:
                    time.sleep(1)
            else:
                sys.exit(1)
        
        elif args.interactive:
            manager.run_interactive_mode()
        
        else:
            # Default: start VOD server only
            if manager.start_vod_server(port=args.vod_port):
                print(f"✅ VOD server running on port {args.vod_port}")
                print("Press Ctrl+C to stop")
                while manager.running:
                    time.sleep(1)
            else:
                sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    finally:
        manager.stop_all_services()

if __name__ == '__main__':
    main()