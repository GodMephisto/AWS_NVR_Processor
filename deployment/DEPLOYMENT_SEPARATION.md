# NVR System Deployment Separation

## 🏠 LOCAL NVR MACHINE (4000H) - Runs on Your Hardware

### Core NVR System
```
nvr-system/
├── __init__.py                    # ✅ NEEDED - Python package structure
├── config/
│   ├── __init__.py               # ✅ NEEDED - For imports
│   └── basic_config.py           # 🏠 LOCAL - Configuration management
├── services/
│   ├── __init__.py               # ✅ NEEDED - For imports
│   ├── cloud_sync.py             # 🏠 LOCAL - Uploads videos to S3
│   ├── metadata_extractor.py     # 🏠 LOCAL - Processes video files
│   ├── vod_streaming.py          # 🏠 LOCAL - Serves video streams
│   └── timelapse_processor.py    # 🏠 LOCAL - Creates timelapses
├── api/
│   ├── __init__.py               # ✅ NEEDED - For imports
│   └── vod_api.py                # 🏠 LOCAL - REST API for video access
├── utils/
│   └── __init__.py               # ✅ NEEDED - For imports
├── web/
│   └── index.html                # 🏠 LOCAL - Web interface
└── test_main.py                  # 🏠 LOCAL - Testing script
```

### Setup & Configuration Files
```
setup_basic_nvr.py                # 🏠 LOCAL - NVR installation script
test_aws_setup.py                 # 🏠 LOCAL - AWS connectivity test
BASIC_NVR_README.md              # 🏠 LOCAL - NVR setup instructions
.env                             # 🏠 LOCAL - Environment variables
requirements.txt                 # 🏠 LOCAL - Python dependencies
```

---

## ☁️ AWS CLOUD - Deployed to AWS Services

### Lambda Functions (Serverless)
```
aws-lambda/
├── lambda_indexer.py            # ☁️ AWS LAMBDA - Video indexing
└── lambda_normalizer.py         # ☁️ AWS LAMBDA - Path normalization
```

### AWS Resources (Manual Setup)
```
AWS_MANUAL_SETUP.md              # ☁️ AWS - Setup instructions
DEPLOYMENT_CHECKLIST.md          # ☁️ AWS - Deployment guide
```

---

## 📋 DOCUMENTATION & SPECS - Development Only

### Specifications
```
.kiro/specs/
├── nvr-edge-processing/         # 📋 DEV - NVR system specs
└── video-on-demand-timelapse/   # 📋 DEV - VOD system specs
```

### Project Management
```
FILE_MANIFEST.md                 # 📋 DEV - File organization
TERRAFORM_MIGRATION_SUMMARY.md   # 📋 DEV - Migration notes
```

---

## 🎯 DEPLOYMENT SUMMARY

### What Goes Where:

**🏠 ON YOUR NVR MACHINE (4000H):**
- Entire `nvr-system/` folder (WITH `__init__.py` files)
- Setup scripts (`setup_basic_nvr.py`, `test_aws_setup.py`)
- Configuration files (`.env`, `requirements.txt`)
- Documentation (`BASIC_NVR_README.md`)

**☁️ IN AWS CLOUD:**
- `aws-lambda/lambda_indexer.py` → Deploy as Lambda function
- `aws-lambda/lambda_normalizer.py` → Deploy as Lambda function
- S3 bucket, DynamoDB table, CloudFront (manual setup)

**📋 DEVELOPMENT ONLY (Don't Deploy):**
- `.kiro/specs/` - Specification documents
- `FILE_MANIFEST.md`, `TERRAFORM_MIGRATION_SUMMARY.md` - Project docs

### Key Points:
- **`__init__.py` files are ONLY needed for local NVR system**
- **AWS Lambda functions are standalone - no `__init__.py` needed**
- **Local system handles video capture/processing**
- **AWS handles cloud storage/indexing/streaming**