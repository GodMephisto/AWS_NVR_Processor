# Manual AWS Deployment Checklist

Since you're manually importing all files to AWS, here's what you need to transfer and set up.

## Files to Transfer to AWS Instance

### Core NVR System Files
```
nvr-system/
├── __init__.py
├── main.py                     # Full system (if needed)
├── test_main.py               # Basic system for testing
├── config/
│   ├── __init__.py
│   ├── basic_config.py        # Simplified configuration
│   └── nvr_config.py         # Full configuration (optional)
├── services/
│   ├── __init__.py
│   ├── metadata_extractor.py  # Video analysis
│   ├── cloud_sync.py         # S3 upload
│   ├── vod_streaming.py      # Video streaming
│   └── timelapse_processor.py # Timelapse creation
├── api/
│   ├── __init__.py
│   └── vod_api.py            # REST API
└── web/
    └── index.html            # Web interface
```

### Setup and Test Scripts
```
setup_basic_nvr.py            # System setup
test_aws_setup.py            # AWS connectivity test
requirements.txt             # Python dependencies
```

### Documentation
```
BASIC_NVR_README.md          # Setup instructions
AWS_MANUAL_SETUP.md          # AWS resource creation
DEPLOYMENT_CHECKLIST.md      # This file
```

### Optional (if using Lambda functions)
```
aws-lambda/
├── lambda_indexer.py        # Video indexing Lambda (Amcrest optimized)
└── lambda_normalizer.py     # Video normalization Lambda (Amcrest optimized)
```

## AWS Instance Setup Steps

### 1. System Preparation
```bash
# Update system
sudo yum update -y  # Amazon Linux
# or
sudo apt update && sudo apt upgrade -y  # Ubuntu

# Install Python 3 and pip
sudo yum install python3 python3-pip -y  # Amazon Linux
# or
sudo apt install python3 python3-pip -y  # Ubuntu

# Install system dependencies
sudo yum install ffmpeg -y  # Amazon Linux (enable EPEL first)
# or
sudo apt install ffmpeg -y  # Ubuntu
```

### 2. Create Directory Structure
```bash
sudo mkdir -p /opt/nvr/{config,logs,storage}
sudo chown -R ec2-user:ec2-user /opt/nvr  # Amazon Linux
# or
sudo chown -R ubuntu:ubuntu /opt/nvr      # Ubuntu
```

### 3. Transfer Files
Upload all the nvr-system files to `/opt/nvr/` on your AWS instance.

### 4. Install Python Dependencies
```bash
cd /opt/nvr
pip3 install -r requirements.txt
```

### 5. Set Environment Variables
```bash
# Add to ~/.bashrc or /etc/environment
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
export S3_BUCKET="your-nvr-videos-bucket"
export DYNAMODB_TABLE="nvr-video-index"
```

### 6. Configure the System
```bash
# Run setup script
python3 setup_basic_nvr.py

# Or manually create config file at /opt/nvr/config/basic_config.json
```

### 7. Test Everything
```bash
# Test AWS connectivity
python3 test_aws_setup.py

# Test camera connections
python3 nvr-system/test_main.py --test-cameras

# Test full system
python3 nvr-system/test_main.py
```

## AWS Resources to Create Manually

### 1. S3 Bucket
- Name: `your-nvr-videos-bucket`
- Region: `us-east-1` (or your preferred region)
- Versioning: Enabled (optional)
- Lifecycle: Delete objects after 365 days (optional)

### 2. DynamoDB Table
- Name: `nvr-video-index`
- Partition Key: `camera_id` (String)
- Sort Key: `start_ts` (String)
- Billing: Pay-per-request

### 3. IAM User/Role
- Name: `nvr-system-user`
- Policies: S3 access to your bucket, DynamoDB access to your table
- Generate access keys

### 4. CloudFront Distribution (Optional)
- Origin: Your S3 bucket
- Behavior: Default settings
- Note the CloudFront domain name

## Security Considerations

### 1. EC2 Instance
- Use security groups to restrict access
- Only open necessary ports (22 for SSH, 8080 for web interface)
- Use key pairs for SSH access
- Consider using IAM roles instead of access keys

### 2. S3 Bucket
- Enable bucket encryption
- Set up bucket policies for restricted access
- Enable access logging

### 3. Network
- Use VPC with private subnets if possible
- Set up NAT gateway for internet access
- Consider VPC endpoints for AWS services

## Monitoring Setup

### 1. CloudWatch Logs
```bash
# Install CloudWatch agent (optional)
sudo yum install amazon-cloudwatch-agent -y
```

### 2. System Logs
- NVR logs: `/opt/nvr/logs/basic_nvr.log`
- System logs: `/var/log/messages` or `/var/log/syslog`

### 3. Metrics to Monitor
- Disk usage in `/opt/nvr/storage`
- CPU and memory usage
- Network bandwidth
- S3 upload success/failure rates

## Troubleshooting

### Common Issues
1. **Permission denied**: Check file ownership and permissions
2. **AWS access denied**: Verify IAM policies and credentials
3. **Camera connection failed**: Check network connectivity and RTSP URLs
4. **Disk space full**: Monitor `/opt/nvr/storage` usage

### Log Locations
- Application logs: `/opt/nvr/logs/`
- System logs: `/var/log/`
- AWS CLI logs: `~/.aws/cli/cache/`

### Useful Commands
```bash
# Check system resources
df -h                    # Disk usage
free -h                  # Memory usage
top                      # CPU usage

# Check NVR system
systemctl status basic-nvr  # If using systemd
ps aux | grep python3       # Check running processes
tail -f /opt/nvr/logs/basic_nvr.log  # Monitor logs

# Test AWS connectivity
aws s3 ls s3://your-bucket-name
aws dynamodb describe-table --table-name nvr-video-index
```

This checklist ensures you have everything needed for manual deployment!