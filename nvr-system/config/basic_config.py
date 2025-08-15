"""
Basic NVR Configuration for 4000H Testing
Simplified configuration focused on Amcrest cameras only
"""

import os
import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import logging

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file manually"""
    env_vars = {}
    env_file = Path('.env')
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key and value:
                            env_vars[key] = value
                            # Only set if not already in environment
                            if key not in os.environ:
                                os.environ[key] = value
        except Exception as e:
            pass  # Ignore errors loading .env file
    return env_vars

# Load .env file
_env_vars = load_env_file()

logger = logging.getLogger(__name__)

@dataclass
class BasicCameraConfig:
    """Basic camera configuration for testing"""
    camera_id: str
    site_id: str
    rtsp_url: str
    username: str = "admin"
    password: str = ""
    enabled: bool = True

@dataclass
class BasicAWSConfig:
    """Basic AWS configuration"""
    region: str = "us-east-1"
    bucket_name: str = ""
    access_key_id: str = ""
    secret_access_key: str = ""
    cloudfront_domain: str = ""
    dynamodb_table: str = "nvr-video-index"

@dataclass
class BasicStorageConfig:
    """Basic storage configuration"""
    base_path: str = "/opt/nvr/storage"
    max_usage_gb: int = 100  # Reduced for testing
    retention_days: int = 3  # Shorter retention for testing

class BasicNVRConfig:
    """Simplified NVR configuration for testing"""
    
    def __init__(self, config_file: str = "/opt/nvr/config/basic_config.json"):
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
        
        # Default configurations
        self.cameras: Dict[str, BasicCameraConfig] = {}
        self.aws = BasicAWSConfig()
        self.storage = BasicStorageConfig()
        
        # Load configuration if file exists
        if self.config_file.exists():
            self.load_config()
        else:
            self.logger.warning(f"Config file {config_file} not found, using defaults")
            self._create_sample_config()
        
        # Load from environment variables (overrides file config)
        self.load_from_environment()
    
    def load_config(self) -> None:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Load cameras
            if 'cameras' in config_data:
                for cam_id, cam_data in config_data['cameras'].items():
                    self.cameras[cam_id] = BasicCameraConfig(**cam_data)
            
            # Load AWS config
            if 'aws' in config_data:
                self.aws = BasicAWSConfig(**config_data['aws'])
            
            # Load storage config
            if 'storage' in config_data:
                self.storage = BasicStorageConfig(**config_data['storage'])
            
            self.logger.info(f"Configuration loaded from {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise
    
    def save_config(self) -> None:
        """Save current configuration to JSON file"""
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                'cameras': {
                    cam_id: {
                        'camera_id': cam.camera_id,
                        'site_id': cam.site_id,
                        'rtsp_url': cam.rtsp_url,
                        'username': cam.username,
                        'password': cam.password,
                        'enabled': cam.enabled
                    } for cam_id, cam in self.cameras.items()
                },
                'aws': {
                    'region': self.aws.region,
                    'bucket_name': self.aws.bucket_name,
                    'access_key_id': self.aws.access_key_id,
                    'secret_access_key': self.aws.secret_access_key,
                    'cloudfront_domain': self.aws.cloudfront_domain
                },
                'storage': {
                    'base_path': self.storage.base_path,
                    'max_usage_gb': self.storage.max_usage_gb,
                    'retention_days': self.storage.retention_days
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            raise
    
    def _create_sample_config(self) -> None:
        """Create a sample configuration file"""
        try:
            # Add sample Amcrest camera
            self.cameras['amcrest_01'] = BasicCameraConfig(
                camera_id='amcrest_01',
                site_id='test_site',
                rtsp_url='rtsp://192.168.1.100:554/cam/realmonitor?channel=1&subtype=0',
                username='admin',
                password='password123'
            )
            
            # Set AWS config from environment variables
            self.aws.bucket_name = os.getenv('S3_BUCKET', '')
            self.aws.access_key_id = os.getenv('AWS_ACCESS_KEY_ID', '')
            self.aws.secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
            self.aws.cloudfront_domain = os.getenv('CLOUDFRONT_DOMAIN', '')
            
            # Save sample config
            self.save_config()
            
            self.logger.info("Created sample configuration file")
            
        except Exception as e:
            self.logger.error(f"Failed to create sample config: {e}")
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate cameras
        if not self.cameras:
            errors.append("No cameras configured")
        
        for cam_id, camera in self.cameras.items():
            if not camera.rtsp_url:
                errors.append(f"Camera {cam_id}: RTSP URL not configured")
            if not camera.site_id:
                errors.append(f"Camera {cam_id}: Site ID not configured")
        
        # Validate AWS configuration
        if not self.aws.bucket_name:
            errors.append("AWS S3 bucket name not configured")
        
        # Validate storage paths
        storage_path = Path(self.storage.base_path)
        if not storage_path.exists():
            try:
                storage_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create storage directory: {e}")
        
        return errors
    
    def test_aws_connectivity(self) -> bool:
        """Test AWS S3 connectivity"""
        if not self.aws.bucket_name:
            return False
            
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            s3_client = boto3.client(
                's3',
                region_name=self.aws.region,
                aws_access_key_id=self.aws.access_key_id,
                aws_secret_access_key=self.aws.secret_access_key
            )
            
            # Test bucket access
            s3_client.head_bucket(Bucket=self.aws.bucket_name)
            logger.info(f"AWS S3 connectivity test passed for bucket: {self.aws.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"AWS S3 connectivity test failed: {e}")
            return False

    def load_from_environment(self):
        """Load configuration from environment variables"""
        try:
            # Load AWS config from environment
            if os.getenv('AWS_ACCESS_KEY_ID'):
                self.aws.access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            if os.getenv('AWS_SECRET_ACCESS_KEY'):
                self.aws.secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            if os.getenv('AWS_REGION'):
                self.aws.region = os.getenv('AWS_REGION')
            if os.getenv('S3_BUCKET'):
                self.aws.bucket_name = os.getenv('S3_BUCKET')
            if os.getenv('CLOUDFRONT_DOMAIN'):
                self.aws.cloudfront_domain = os.getenv('CLOUDFRONT_DOMAIN')
            if os.getenv('DYNAMODB_TABLE'):
                self.aws.dynamodb_table = os.getenv('DYNAMODB_TABLE')
                
            logger.info("Loaded configuration from environment variables")
        except Exception as e:
            logger.debug(f"Could not load environment variables: {e}")

# Global configuration instance
config = BasicNVRConfig()