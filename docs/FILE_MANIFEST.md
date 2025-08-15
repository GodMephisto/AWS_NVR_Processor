# File Manifest for Manual Transfer

Complete list of files to transfer to your AWS instance for the NVR system.

## Essential Files (Required)

### Core System
- `nvr-system/__init__.py` - Package initialization
- `nvr-system/test_main.py` - Main application (basic version)
- `requirements.txt` - Python dependencies

### Configuration
- `nvr-system/config/__init__.py` - Config package init
- `nvr-system/config/basic_config.py` - Configuration management

### Services
- `nvr-system/services/__init__.py` - Services package init
- `nvr-system/services/metadata_extractor.py` - Video analysis (Amcrest optimized)
- `nvr-system/services/cloud_sync.py` - AWS S3 upload service

### Setup Scripts
- `setup_basic_nvr.py` - System setup script
- `test_aws_setup.py` - AWS connectivity test

### Documentation
- `BASIC_NVR_README.md` - Setup and usage guide
- `AWS_MANUAL_SETUP.md` - AWS resource creation guide
- `DEPLOYMENT_CHECKLIST.md` - Deployment steps
- `FILE_MANIFEST.md` - This file

## Optional Files (Enhanced Features)

### Advanced Services
- `nvr-system/services/vod_streaming.py` - Video-on-demand streaming
- `nvr-system/services/timelapse_processor.py` - Timelapse creation
- `nvr-system/services/hardware_encoder.py` - Hardware encoding (if needed)

### Web Interface
- `nvr-system/api/__init__.py` - API package init
- `nvr-system/api/vod_api.py` - REST API for video access
- `nvr-system/web/index.html` - Web interface

### Full System
- `nvr-system/main.py` - Full system with all features
- `nvr-system/config/nvr_config.py` - Advanced configuration

## Lambda Functions (If Using)

### AWS Lambda Code
- `aws-lambda/lambda_indexer.py` - Video indexing function (Amcrest optimized)
- `aws-lambda/lambda_normalizer.py` - Video normalization function (Amcrest optimized)

## Files NOT Needed

### Development/Testing Only
- `.kiro/` - Kiro IDE specifications (not needed on server)
- `aws-iot-simulator/` - IoT simulator (unrelated to NVR)
- `certificates/` - IoT certificates (unrelated to NVR)
- `scripts/` - Development scripts
- `.env.example` - Example environment file
- `terraform/` - Terraform files (removed - you're doing manual setup)

### Documentation (Optional)
- `README.md` - General project readme
- `.kiro/specs/` - Development specifications

## Minimal Transfer List (For Basic Testing)

If you want to start with just the essentials:

```
nvr-system/
├── __init__.py
├── test_main.py
├── config/
│   ├── __init__.py
│   └── basic_config.py
└── services/
    ├── __init__.py
    ├── metadata_extractor.py
    └── cloud_sync.py

setup_basic_nvr.py
test_aws_setup.py
requirements.txt
BASIC_NVR_README.md
AWS_MANUAL_SETUP.md
DEPLOYMENT_CHECKLIST.md
```

This minimal set gives you:
- Basic NVR functionality
- Amcrest camera support
- AWS S3 upload
- Video metadata extraction
- System setup and testing

## File Sizes (Approximate)

- Core Python files: ~50KB total
- Documentation: ~30KB total
- Setup scripts: ~15KB total
- **Total essential files: ~100KB**

Very lightweight for manual transfer!