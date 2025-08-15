# Manual AWS Setup Guide (No Terraform Required)

Since you have organizational privileges, you can set up the AWS resources manually through the AWS Console or CLI.

## Required AWS Resources

### 1. S3 Bucket for Video Storage

**AWS Console:**
1. Go to S3 Console
2. Click "Create bucket"
3. Bucket name: `your-nvr-videos-bucket` (must be globally unique)
4. Region: Choose your preferred region (e.g., us-east-1)
5. Keep default settings
6. Click "Create bucket"

**AWS CLI:**
```bash
aws s3 mb s3://your-nvr-videos-bucket --region us-east-1
```

### 2. DynamoDB Table for Video Index (Optional)

**AWS Console:**
1. Go to DynamoDB Console
2. Click "Create table"
3. Table name: `nvr-video-index`
4. Partition key: `camera_id` (String)
5. Sort key: `start_ts` (String)
6. Use default settings
7. Click "Create table"

**AWS CLI:**
```bash
aws dynamodb create-table \
    --table-name nvr-video-index \
    --attribute-definitions \
        AttributeName=camera_id,AttributeType=S \
        AttributeName=start_ts,AttributeType=S \
    --key-schema \
        AttributeName=camera_id,KeyType=HASH \
        AttributeName=start_ts,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST
```

### 3. IAM User for NVR System

**AWS Console:**
1. Go to IAM Console
2. Click "Users" → "Add users"
3. Username: `nvr-system-user`
4. Access type: "Programmatic access"
5. Attach policies:
   - `AmazonS3FullAccess` (or create custom policy below)
   - `AmazonDynamoDBFullAccess` (if using DynamoDB)
6. Download credentials CSV file

**Custom S3 Policy (More Secure):**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-nvr-videos-bucket",
                "arn:aws:s3:::your-nvr-videos-bucket/*"
            ]
        }
    ]
}
```

### 4. CloudFront Distribution (Optional - for VOD streaming)

**AWS Console:**
1. Go to CloudFront Console
2. Click "Create distribution"
3. Origin domain: Select your S3 bucket
4. Origin access: "Origin access control settings"
5. Create new OAC (Origin Access Control)
6. Default cache behavior: Keep defaults
7. Click "Create distribution"
8. Note the CloudFront domain name (e.g., d123456789.cloudfront.net)

## Configuration

After creating the AWS resources, update your NVR configuration:

### Environment Variables
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_REGION="us-east-1"
export S3_BUCKET="your-nvr-videos-bucket"
export DYNAMODB_TABLE="nvr-video-index"
export CLOUDFRONT_DOMAIN="d123456789.cloudfront.net"
```

### Configuration File
Update `/opt/nvr/config/basic_config.json`:
```json
{
  "cameras": {
    "amcrest_01": {
      "camera_id": "amcrest_01",
      "site_id": "test_site",
      "rtsp_url": "rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0",
      "username": "admin",
      "password": "password",
      "enabled": true
    }
  },
  "aws": {
    "region": "us-east-1",
    "bucket_name": "your-nvr-videos-bucket",
    "access_key_id": "your-access-key-id",
    "secret_access_key": "your-secret-access-key",
    "cloudfront_domain": "d123456789.cloudfront.net",
    "dynamodb_table": "nvr-video-index"
  },
  "storage": {
    "base_path": "/opt/nvr/storage",
    "max_usage_gb": 100,
    "retention_days": 3
  }
}
```

## Testing AWS Connection

Test your AWS setup:
```bash
# Test S3 access
aws s3 ls s3://your-nvr-videos-bucket

# Test DynamoDB access
aws dynamodb describe-table --table-name nvr-video-index

# Test with NVR system
python3 nvr-system/test_main.py --test-aws
```

## Cost Considerations

### S3 Storage Costs (Approximate)
- Standard storage: $0.023 per GB/month
- 100GB of video: ~$2.30/month
- Data transfer out: $0.09 per GB (first 1GB free)

### DynamoDB Costs
- Pay-per-request: $0.25 per million read requests
- $1.25 per million write requests
- Minimal cost for video indexing

### CloudFront Costs
- First 1TB/month: $0.085 per GB
- Minimal cost for video streaming

## Security Best Practices

1. **Use IAM roles instead of access keys** (if running on EC2)
2. **Enable S3 bucket encryption**
3. **Set up S3 bucket policies** to restrict access
4. **Enable CloudTrail** for audit logging
5. **Use VPC endpoints** for private AWS access

## Backup and Disaster Recovery

1. **Enable S3 versioning** for video files
2. **Set up cross-region replication** for critical videos
3. **Regular DynamoDB backups**
4. **Monitor with CloudWatch**

This manual setup gives you full control without Terraform dependencies!