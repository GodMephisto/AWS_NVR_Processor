#!/usr/bin/env python3
"""
Simple AWS Test - No virtual environment dependencies
"""

import os
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded .env file")
except ImportError:
    print("python-dotenv not available, using system environment")

try:
    import boto3
    print("boto3 imported successfully")
    
    # Test AWS credentials
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    print(f"AWS Account: {identity['Account']}")
    print(f"AWS User: {identity['Arn']}")
    
    # Test environment variables
    aws_region = os.getenv('AWS_REGION')
    s3_bucket = os.getenv('AWS_S3_BUCKET')
    
    print(f"AWS_REGION: {aws_region}")
    print(f"AWS_S3_BUCKET: {s3_bucket}")
    
    if aws_region and s3_bucket:
        print("SUCCESS: AWS setup is working correctly!")
        
        # Test S3 access
        s3 = boto3.client('s3')
        buckets = s3.list_buckets()
        print(f"Found {len(buckets['Buckets'])} S3 buckets")
        
        bucket_names = [b['Name'] for b in buckets['Buckets']]
        if s3_bucket in bucket_names:
            print(f"SUCCESS: Target bucket '{s3_bucket}' exists")
        else:
            print(f"WARNING: Target bucket '{s3_bucket}' not found")
            
    else:
        print("WARNING: Missing environment variables")
        
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"AWS error: {e}")