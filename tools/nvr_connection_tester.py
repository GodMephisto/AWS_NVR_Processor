#!/usr/bin/env python3
"""
NVR Connection Tester
Tests network connectivity to NVR systems and cameras
"""

import os
import sys
import socket
import subprocess
import ipaddress
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NVRConnectionTester:
    def __init__(self):
        self.discovered_devices = []
    
    def ping_host(self, host, timeout=3):
        """Ping a host to check if it's reachable"""
        try:
            if sys.platform == "win32":
                result = subprocess.run(['ping', '-n', '1', '-w', str(timeout * 1000), host], 
                                      capture_output=True, text=True, timeout=timeout + 2)
            else:
                result = subprocess.run(['ping', '-c', '1', '-W', str(timeout), host], 
                                      capture_output=True, text=True, timeout=timeout + 2)
            return result.returncode == 0
        except Exception:
            return False
    
    def scan_network(self, network_base="192.168.1", start=1, end=254):
        """Scan network for active devices"""
        logger.info(f"Scanning network {network_base}.{start}-{end}...")
        
        devices = []
        try:
            for i in range(start, end + 1):
                ip = f"{network_base}.{i}"
                if self.ping_host(ip, timeout=1):
                    devices.append(ip)
                    logger.info(f"   Found device: {ip}")
        
        except Exception as e:
            logger.error(f"Network scan failed: {e}")
        
        return devices
    
    def test_port(self, host, port, timeout=3):
        """Test if a specific port is open on a host"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def test_web_interface(self, host, ports_to_test=[80, 8080, 443, 8443]):
        """Test for web interface on common ports"""
        logger.info(f"Testing web interface on {host}...")
        
        for port in ports_to_test:
            if self.test_port(host, port):
                logger.info(f"   Web interface found on {host}:{port}")
                return port
        
        return None
    
    def test_rtsp_port(self, host):
        """Test if device has RTSP port (likely camera)"""
        if self.test_port(host, 554):
            logger.info(f"   RTSP port open on {host}:554")
            return True
        return False
    
    def test_smb_shares(self, host):
        """Test for SMB shares (NVR storage)"""
        try:
            if sys.platform == "win32":
                # Test SMB connection
                result = subprocess.run(['net', 'view', f'\\\\{host}'], 
                                      capture_output=True, text=True, timeout=10, shell=True)
                
                if result.returncode == 0:
                    logger.info(f"   SMB shares available on {host}")
                    
                    # Try to access specific share
                    test_path = f"\\\\{host}\\VideoStorage"
                    result2 = subprocess.run(['dir', test_path], 
                                           capture_output=True, text=True, timeout=10, shell=True)
                    if result2.returncode == 0:
                        logger.info(f"   VideoStorage share accessible: {test_path}")
                        return test_path
                    
                    return True
        except Exception as e:
            logger.debug(f"SMB test failed for {host}: {e}")
        
        return False
    
    def identify_device_type(self, host):
        """Try to identify what type of device this is"""
        device_info = {
            'ip': host,
            'type': 'unknown',
            'services': []
        }
        
        # Test web interface
        web_port = self.test_web_interface(host)
        if web_port:
            device_info['services'].append(f'web:{web_port}')
        
        # Test RTSP (camera)
        if self.test_rtsp_port(host):
            device_info['services'].append('rtsp:554')
            device_info['type'] = 'camera'
        
        # Test SMB (NVR)
        smb_result = self.test_smb_shares(host)
        if smb_result:
            device_info['services'].append('smb')
            device_info['type'] = 'nvr'
        
        return device_info
    
    def auto_discover(self, networks=["192.168.1", "192.168.0", "10.0.1"]):
        """Auto-discover NVR and camera devices"""
        logger.info("Starting auto-discovery...")
        
        all_devices = []
        
        for network in networks:
            logger.info(f"Scanning network {network}.0/24...")
            devices = self.scan_network(network)
            
            for device in devices:
                logger.info(f"Analyzing device {device}...")
                device_info = self.identify_device_type(device)
                all_devices.append(device_info)
        
        # Summarize findings
        logger.info("\nDiscovery Summary:")
        logger.info("=" * 40)
        
        nvr_devices = [d for d in all_devices if d['type'] == 'nvr']
        camera_devices = [d for d in all_devices if d['type'] == 'camera']
        other_devices = [d for d in all_devices if d['type'] == 'unknown']
        
        if nvr_devices:
            logger.info("NVR Devices Found:")
            for device in nvr_devices:
                logger.info(f"  {device['ip']} - Services: {', '.join(device['services'])}")
        
        if camera_devices:
            logger.info("Camera Devices Found:")
            for device in camera_devices:
                logger.info(f"  {device['ip']} - Services: {', '.join(device['services'])}")
        
        if other_devices:
            logger.info("Other Devices Found:")
            for device in other_devices:
                logger.info(f"  {device['ip']} - Services: {', '.join(device['services'])}")
        
        if not all_devices:
            logger.info("No devices found. Check network configuration.")
        
        return all_devices
    
    def test_specific_nvr(self, nvr_ip):
        """Test a specific NVR IP address"""
        logger.info(f"Testing specific NVR: {nvr_ip}")
        
        if not self.ping_host(nvr_ip):
            logger.error(f"Cannot reach {nvr_ip}")
            return False
        
        logger.info(f"PASS {nvr_ip} is reachable")
        
        # Test services
        device_info = self.identify_device_type(nvr_ip)
        
        logger.info(f"Device type: {device_info['type']}")
        logger.info(f"Services: {', '.join(device_info['services'])}")
        
        return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NVR Connection Tester')
    parser.add_argument('--auto-discover', action='store_true', help='Auto-discover devices')
    parser.add_argument('--nvr-ip', help='Test specific NVR IP address')
    parser.add_argument('--scan-network', help='Scan specific network (e.g., 192.168.1)')
    
    args = parser.parse_args()
    
    tester = NVRConnectionTester()
    
    try:
        if args.auto_discover:
            tester.auto_discover()
        elif args.nvr_ip:
            tester.test_specific_nvr(args.nvr_ip)
        elif args.scan_network:
            devices = tester.scan_network(args.scan_network)
            logger.info(f"Found {len(devices)} devices: {devices}")
        else:
            print("NVR Connection Tester")
            print("Use --auto-discover to scan for devices")
            print("Use --nvr-ip <ip> to test specific NVR")
            print("Use --scan-network <network> to scan specific network")
            print("Use --help for more options")
    
    except KeyboardInterrupt:
        logger.info("Scan interrupted by user")
    except Exception as e:
        logger.error(f"Connection tester error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()