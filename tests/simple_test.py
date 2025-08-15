#!/usr/bin/env python3
"""
Simple test to verify the environment is working
"""

import boto3
import os
from dotenv import load_dotenv

def main():
    print("Testing clean environment...")
    
    # Load environment variables
    load_dotenv()
    
    # Test AWS connection
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"SUCCESS: AWS connection working")
        print(f"Account: {identity['Account']}")
        
        # Test environment variables
        region = os.getenv('AWS_REGION')
        bucket = os.getenv('AWS_S3_BUCKET')
        
        print(f"AWS_REGION: {region}")
        print(f"AWS_S3_BUCKET: {bucket}")
        
        print("Environment is clean and working!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)