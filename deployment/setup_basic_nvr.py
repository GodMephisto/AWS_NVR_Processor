#!/usr/bin/env python3
"""
Setup script for Basic NVR System
Configures the system for 4000H testing with Amcrest cameras
"""

import os
import json
import sys
from pathlib import Path

def create_directories():
    """Create necessary directories"""
    directories = [
        "/opt/nvr",
        "/opt/nvr/config",
        "/opt/nvr/logs",
        "/opt/nvr/storage"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

def create_basic_config():
    """Create basic configuration file"""
    config_path = "/opt/nvr/config/basic_config.json"
    
    # Get AWS credentials from environment or prompt
    aws_bucket = os.getenv('S3_BUCKET') or input("Enter S3 bucket name (optional): ").strip()
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID') or input("Enter AWS Access Key ID (optional): ").strip()
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') or input("Enter AWS Secret Access Key (optional): ").strip()
    aws_region = os.getenv('AWS_REGION') or input("Enter AWS region [us-east-1]: ").strip() or "us-east-1"
    
    # Get camera configuration
    print("\nCamera Configuration:")
    camera_ip = input("Enter Amcrest camera IP address [192.168.1.100]: ").strip() or "192.168.1.100"
    camera_username = input("Enter camera username [admin]: ").strip() or "admin"
    camera_password = input("Enter camera password: ").strip()
    
    config = {
        "cameras": {
            "amcrest_01": {
                "camera_id": "amcrest_01",
                "site_id": "test_site",
                "rtsp_url": f"rtsp://{camera_username}:{camera_password}@{camera_ip}:554/cam/realmonitor?channel=1&subtype=0",
                "username": camera_username,
                "password": camera_password,
                "enabled": True
            }
        },
        "aws": {
            "region": aws_region,
            "bucket_name": aws_bucket,
            "access_key_id": aws_access_key,
            "secret_access_key": aws_secret_key,
            "cloudfront_domain": ""
        },
        "storage": {
            "base_path": "/opt/nvr/storage",
            "max_usage_gb": 100,
            "retention_days": 3
        }
    }
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Created configuration file: {config_path}")

def install_dependencies():
    """Install required Python packages"""
    packages = [
        "opencv-python",
        "boto3",
        "requests",
        "flask",
        "flask-cors"
    ]
    
    print("Installing Python dependencies...")
    for package in packages:
        os.system(f"pip install {package}")
        print(f"Installed: {package}")

def create_systemd_service():
    """Create systemd service file"""
    service_content = """[Unit]
Description=Basic NVR System for 4000H Testing
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nvr
ExecStart=/usr/bin/python3 /path/to/nvr-system/test_main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_path = "/etc/systemd/system/basic-nvr.service"
    
    try:
        with open(service_path, 'w') as f:
            f.write(service_content)
        print(f"Created systemd service: {service_path}")
        print("To enable the service, run:")
        print("  sudo systemctl enable basic-nvr")
        print("  sudo systemctl start basic-nvr")
    except PermissionError:
        print("Note: Run as root to create systemd service file")

def main():
    """Main setup function"""
    print("Setting up Basic NVR System for 4000H Testing")
    print("=" * 50)
    
    try:
        # Create directories
        print("\n1. Creating directories...")
        create_directories()
        
        # Install dependencies
        print("\n2. Installing dependencies...")
        install_dependencies()
        
        # Create configuration
        print("\n3. Creating configuration...")
        create_basic_config()
        
        # Create systemd service
        print("\n4. Creating systemd service...")
        create_systemd_service()
        
        print("\n" + "=" * 50)
        print("Setup completed successfully!")
        print("\nNext steps:")
        print("1. Test camera connection:")
        print("   python3 nvr-system/test_main.py --test-cameras")
        print("\n2. Start the system:")
        print("   python3 nvr-system/test_main.py")
        print("\n3. Or use systemd service:")
        print("   sudo systemctl start basic-nvr")
        
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()