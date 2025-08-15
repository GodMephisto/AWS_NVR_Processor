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
        logger.info("Starting VOD streaming server...")
        
        try:
            process = subprocess.Popen([
                sys.executable,
                str(self.base_path / "nvr_vod_server.py"),
                "--host", host,
                "--port", str(port)
            ])
            
            self.processes['vod_server'] = process
            logger.info(f"VOD server started on {host}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start VOD server: {e}")
            return False
    
    def stop_vod_server(self):
        """Stop the VOD streaming server"""
        if 'vod_server' in self.processes:
            try:
                self.processes['vod_server'].terminate()
                self.processes['vod_server'].wait(timeout=10)
                del self.processes['vod_server']
                logger.info("VOD server stopped")
                return True
            except Exception as e:
                logger.error(f"Error stopping VOD server: {e}")
                return False
        return True
    
    def start_all_services(self, host='127.0.0.1', vod_port=8080):
        """Start all NVR services"""
        logger.info("Starting all NVR services...")
        
        success = True
        
        # Start VOD server
        if not self.start_vod_server(host, vod_port):
            success = False
        
        if success:
            logger.info("All services started successfully")
            self.running = True
        else:
            logger.error("Some services failed to start")
            
        return success
    
    def stop_all_services(self):
        """Stop all NVR services"""
        logger.info("Stopping all NVR services...")
        
        self.running = False
        
        # Stop VOD server
        self.stop_vod_server()
        
        # Stop any other processes
        for name, process in list(self.processes.items()):
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
                try:
                    process.kill()
                except:
                    pass
        
        self.processes.clear()
        logger.info("All services stopped")
    
    def get_status(self):
        """Get status of all services"""
        status = {
            'running': self.running,
            'services': {}
        }
        
        for name, process in self.processes.items():
            try:
                # Check if process is still running
                if process.poll() is None:
                    status['services'][name] = 'running'
                else:
                    status['services'][name] = 'stopped'
            except Exception:
                status['services'][name] = 'unknown'
        
        return status
    
    def run_interactive(self):
        """Run in interactive mode"""
        print("NVR System Manager - Interactive Mode")
        print("=" * 40)
        
        while True:
            print("\nOptions:")
            print("1. Start VOD server")
            print("2. Stop VOD server")
            print("3. Start all services")
            print("4. Stop all services")
            print("5. Show status")
            print("6. Exit")
            
            try:
                choice = input("\nEnter choice (1-6): ").strip()
                
                if choice == '1':
                    host = input("Host (127.0.0.1): ").strip() or '127.0.0.1'
                    port = input("Port (8080): ").strip() or '8080'
                    self.start_vod_server(host, int(port))
                
                elif choice == '2':
                    self.stop_vod_server()
                
                elif choice == '3':
                    host = input("Host (127.0.0.1): ").strip() or '127.0.0.1'
                    port = input("VOD Port (8080): ").strip() or '8080'
                    self.start_all_services(host, int(port))
                
                elif choice == '4':
                    self.stop_all_services()
                
                elif choice == '5':
                    status = self.get_status()
                    print(f"\nSystem Status:")
                    print(f"Running: {status['running']}")
                    for service, state in status['services'].items():
                        print(f"{service}: {state}")
                
                elif choice == '6':
                    print("Stopping all services...")
                    self.stop_all_services()
                    print("Goodbye!")
                    break
                
                else:
                    print("Invalid choice. Please enter 1-6.")
                    
            except KeyboardInterrupt:
                print("\nStopping all services...")
                self.stop_all_services()
                break
            except Exception as e:
                print(f"Error: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NVR System Manager')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('--start-all', action='store_true', help='Start all services')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--vod-port', type=int, default=8080, help='VOD server port')
    
    args = parser.parse_args()
    
    manager = NVRSystemManager()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        manager.stop_all_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.interactive:
            manager.run_interactive()
        elif args.start_all:
            if manager.start_all_services(args.host, args.vod_port):
                logger.info("All services started. Press Ctrl+C to stop.")
                try:
                    while manager.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
                finally:
                    manager.stop_all_services()
            else:
                logger.error("Failed to start services")
                sys.exit(1)
        else:
            print("NVR System Manager")
            print("Use --interactive for interactive mode or --start-all to start all services")
            print("Use --help for more options")
    
    except Exception as e:
        logger.error(f"System manager error: {e}")
        manager.stop_all_services()
        sys.exit(1)

if __name__ == "__main__":
    main()