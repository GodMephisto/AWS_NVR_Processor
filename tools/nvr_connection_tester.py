#!/usr/bin/env python3
"""
NVR Connection Tester
Tests connectivity to NVR and cameras before full deployment
"""

import os
import sys
import socket
import subprocess
import time
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NVRConnectionTester:
    def __init__(self):
        self.nvr_ip = None
        self.camera_ips = []
        self.storage_path = None
        
    def scan_network(self, network_base="192.168.1"):
        """Scan network for potential NVR/camera devices"""
        logger.info(f"🔍 Scanning network {network_base}.x...")
        
        devices = []
        
        # Use ARP table to find active devices
        try:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            for line in lines:
                if network_base in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[0].strip('()')
                        if self.ping_host(ip, timeout=1):
                            devices.append(ip)
                            logger.info(f"   📡 Found device: {ip}")
        
        except Exception as e:
            logger.error(f"❌ Network scan failed: {e}")
        
        return devices
    
    def ping_host(self, host, timeout=3):
        """Test if host is reachable"""
        try:
            if os.name == 'nt':  # Windows
                result = subprocess.run(['ping', '-n', '1', '-w', str(timeout*1000), host], 
                                      capture_output=True, text=True)
            else:  # Linux/Mac
                result = subprocess.run(['ping', '-c', '1', '-W', str(timeout), host], 
                                      capture_output=True, text=True)
            
            return result.returncode == 0
        except Exception:
            return False
    
    def test_port(self, host, port, timeout=3):
        """Test if specific port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def test_web_interface(self, host):
        """Test if device has web interface (likely NVR)"""
        ports_to_test = [80, 8080, 443, 8000, 8443]
        
        for port in ports_to_test:
            if self.test_port(host, port):
                logger.info(f"   🌐 Web interface found on {host}:{port}")
                return port
        
        return None
    
    def test_rtsp_port(self, host):
        """Test if device has RTSP port (likely camera)"""
        if self.test_port(host, 554):
            logger.info(f"   📹 RTSP port open on {host}:554")
            return True
        return False
    
    def test_smb_share(self, host, share_name="VideoStorage"):
        """Test SMB/CIFS file sharing"""
        try:
            # Try to list shares
            if os.name == 'nt':  # Windows
                result = subprocess.run(['net', 'view', f'\\\\{host}'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info(f"   📁 SMB shares available on {host}")
                    
                    # Try to access specific share
                    test_path = f"\\\\{host}\\{share_name}"
                    try:
                        result2 = subprocess.run(['dir', test_path], 
                                               capture_output=True, text=True, timeout=10, shell=True)
                        if result2.returncode == 0:
                            logger.info(f"   ✅ VideoStorage share accessible: {test_path}")
                            return test_path
                        else:
                            logger.info(f"   ⚠️  Share exists but may need credentials")
                    except Exception:
                        pass
                    
                    return True
            
        except Exception as e:
            logger.debug(f"SMB test failed for {host}: {e}")
        
        return False
    
    def identify_device_type(self, host):
        """Try to identify if device is NVR or camera"""
        device_info = {
            'ip': host,
            'type': 'unknown',
            'services': []
        }
        
        # Test web interface
        web_port = self.test_web_interface(host)
        if web_port:
            device_info['services'].append(f'web:{web_port}')
        
        # Test RTSP
        if self.test_rtsp_port(host):
            device_info['services'].append('rtsp:554')
            device_info['type'] = 'camera'  # Likely a camera
        
        # Test SMB
        smb_result = self.test_smb_share(host)
        if smb_result:
            device_info['services'].append('smb')
            device_info['type'] = 'nvr'  # Likely an NVR
        
        # Test FTP
        if self.test_port(host, 21):
            device_info['services'].append('ftp:21')
        
        return device_info
    
    def auto_discover_nvr_setup(self):
        """Automatically discover NVR and cameras on network"""
        logger.info("🚀 Auto-discovering NVR setup...")
        
        # Scan network
        devices = self.scan_network()
        
        if not devices:
            logger.warning("❌ No devices found on network")
            return None
        
        # Identify each device
        nvr_candidates = []
        camera_candidates = []
        
        for device_ip in devices:
            logger.info(f"🔍 Testing device: {device_ip}")
            device_info = self.identify_device_type(device_ip)
            
            logger.info(f"   Type: {device_info['type']}")
            logger.info(f"   Services: {', '.join(device_info['services'])}")
            
            if device_info['type'] == 'nvr':
                nvr_candidates.append(device_info)
            elif device_info['type'] == 'camera':
                camera_candidates.append(device_info)
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("📊 Discovery Results:")
        logger.info("="*50)
        
        if nvr_candidates:
            logger.info(f"🏠 NVR Candidates ({len(nvr_candidates)}):")
            for nvr in nvr_candidates:
                logger.info(f"   📦 {nvr['ip']} - Services: {', '.join(nvr['services'])}")
        
        if camera_candidates:
            logger.info(f"📹 Camera Candidates ({len(camera_candidates)}):")
            for cam in camera_candidates:
                logger.info(f"   📷 {cam['ip']} - Services: {', '.join(cam['services'])}")
        
        return {
            'nvr_candidates': nvr_candidates,
            'camera_candidates': camera_candidates
        }
    
    def test_specific_nvr(self, nvr_ip, username="admin", password=""):
        """Test connection to specific NVR"""
        logger.info(f"🔍 Testing NVR connection: {nvr_ip}")
        
        results = {
            'ping': False,
            'web_interface': False,
            'smb_share': False,
            'video_files': False
        }
        
        # Test ping
        if self.ping_host(nvr_ip):
            results['ping'] = True
            logger.info("   ✅ Ping successful")
        else:
            logger.error("   ❌ Ping failed")
            return results
        
        # Test web interface
        web_port = self.test_web_interface(nvr_ip)
        if web_port:
            results['web_interface'] = web_port
            logger.info(f"   ✅ Web interface accessible on port {web_port}")
        
        # Test SMB share
        share_path = self.test_smb_share(nvr_ip)
        if share_path:
            results['smb_share'] = share_path
            logger.info(f"   ✅ SMB share accessible: {share_path}")
            
            # Test for video files
            try:
                if isinstance(share_path, str) and share_path.startswith('\\\\'):
                    # Try to find video files
                    result = subprocess.run(['dir', share_path, '/s', '*.dav'], 
                                          capture_output=True, text=True, timeout=30, shell=True)
                    if '.dav' in result.stdout.lower():
                        results['video_files'] = True
                        logger.info("   ✅ Video files found (.dav)")
                    else:
                        logger.info("   ⚠️  No .dav files found yet")
            except Exception as e:
                logger.debug(f"Video file search failed: {e}")
        
        return results
    
    def generate_config(self, discovery_results):
        """Generate configuration based on discovery results"""
        if not discovery_results:
            return None
        
        config_lines = [
            "# NVR System Configuration",
            "# Generated by NVR Connection Tester",
            f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "# NVR Configuration"
        ]
        
        nvr_candidates = discovery_results.get('nvr_candidates', [])
        camera_candidates = discovery_results.get('camera_candidates', [])
        
        if nvr_candidates:
            nvr = nvr_candidates[0]  # Use first NVR found
            config_lines.extend([
                f"NVR_HOST={nvr['ip']}",
                f"NVR_STORAGE_PATH=\\\\\\\\{nvr['ip']}\\\\VideoStorage",
                "NVR_USERNAME=admin",
                "NVR_PASSWORD=your_password",
                ""
            ])
        
        if camera_candidates:
            config_lines.append("# Camera Configuration")
            for i, camera in enumerate(camera_candidates, 1):
                cam_id = f"amcrest_{i:03d}"
                config_lines.extend([
                    f"CAMERA_{cam_id}_IP={camera['ip']}",
                    f"CAMERA_{cam_id}_RTSP=rtsp://admin:password@{camera['ip']}:554/cam/realmonitor?channel=1&subtype=0",
                    f"CAMERA_{cam_id}_SITE_ID=home",
                    f"CAMERA_{cam_id}_ENABLED=true",
                    ""
                ])
        
        config_lines.extend([
            "# AWS Configuration (update with your values)",
            "AWS_REGION=us-east-1",
            "AWS_S3_BUCKET=your-nvr-bucket",
            "AWS_ACCESS_KEY_ID=your_access_key",
            "AWS_SECRET_ACCESS_KEY=your_secret_key"
        ])
        
        return '\n'.join(config_lines)
    
    def run_full_test(self):
        """Run complete NVR connection test"""
        logger.info("🚀 Starting NVR Connection Test")
        logger.info("="*50)
        
        # Auto-discover
        discovery_results = self.auto_discover_nvr_setup()
        
        if discovery_results:
            # Generate configuration
            config = self.generate_config(discovery_results)
            
            if config:
                # Save configuration
                config_file = Path('.env.discovered')
                with open(config_file, 'w') as f:
                    f.write(config)
                
                logger.info(f"\n✅ Configuration saved to: {config_file}")
                logger.info("📝 Review and update passwords, then rename to .env")
        
        logger.info("\n🎯 Next Steps:")
        logger.info("1. Review discovered devices above")
        logger.info("2. Update .env.discovered with correct passwords")
        logger.info("3. Rename .env.discovered to .env")
        logger.info("4. Test with: python src/nvr_system_manager.py --interactive")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NVR Connection Tester')
    parser.add_argument('--nvr-ip', help='Test specific NVR IP address')
    parser.add_argument('--scan-network', help='Network to scan (e.g., 192.168.1)', default='192.168.1')
    parser.add_argument('--auto-discover', action='store_true', help='Auto-discover NVR setup')
    
    args = parser.parse_args()
    
    tester = NVRConnectionTester()
    
    if args.nvr_ip:
        # Test specific NVR
        results = tester.test_specific_nvr(args.nvr_ip)
        logger.info(f"\n📊 Test Results for {args.nvr_ip}:")
        for test, result in results.items():
            status = "✅" if result else "❌"
            logger.info(f"   {status} {test}: {result}")
    
    elif args.auto_discover:
        # Auto-discover setup
        tester.run_full_test()
    
    else:
        # Default: scan network
        devices = tester.scan_network(args.scan_network)
        if devices:
            logger.info(f"\n📡 Found {len(devices)} devices:")
            for device in devices:
                logger.info(f"   🔍 {device}")
            logger.info("\nRun with --auto-discover to identify device types")
        else:
            logger.warning("❌ No devices found")

if __name__ == '__main__':
    main()