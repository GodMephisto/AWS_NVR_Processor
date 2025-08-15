#!/usr/bin/env python3
"""
AWS Setup Test
Tests AWS connectivity and configuration for NVR system
"""

import os
import sys
import boto3
import json
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError

# Fix Windows terminal encoding issues
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")  # Set UTF-8 encoding
    
# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("WARNING: python-dotenv not installed, using system environment variables only")

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class AWSSetupTester:
    def __init__(self):
        self.s3_client = None
        self.dynamodb_client = None
        self.lambda_client = None
        
    def test_credentials(self):
        """Test AWS credentials"""
        print("Testing AWS Credentials...")
        
        try:
            # Try to create STS client to test credentials
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            
            print(f"PASS AWS credentials valid")
            print(f"   Account: {identity['Account']}")
            print(f"   User: {identity['Arn']}")
            return True
            
        except NoCredentialsError:
            print("FAIL No AWS credentials found")
            print("   Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            return False
        except Exception as e:
            print(f"FAIL AWS credentials error: {e}")
            return False
    
    def test_s3_access(self):
        """Test S3 access"""
        print("\nTesting S3 Access...")
        
        try:
            self.s3_client = boto3.client('s3')
            
            # List buckets to test access
            response = self.s3_client.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            
            print(f"PASS S3 access successful")
            print(f"   Found {len(buckets)} buckets")
            
            # Check for NVR bucket
            nvr_bucket = os.getenv('AWS_S3_BUCKET')
            if nvr_bucket:
                if nvr_bucket in buckets:
                    print(f"   PASS NVR bucket '{nvr_bucket}' exists")
                else:
                    print(f"   WARNING NVR bucket '{nvr_bucket}' not found")
            
            return True
            
        except Exception as e:
            print(f"FAIL S3 access failed: {e}")
            return False
    
    def test_dynamodb_access(self):
        """Test DynamoDB access"""
        print("\nTesting DynamoDB Access...")
        
        try:
            self.dynamodb_client = boto3.client('dynamodb')
            
            # List tables to test access
            response = self.dynamodb_client.list_tables()
            tables = response['TableNames']
            
            print(f"PASS DynamoDB access successful")
            print(f"   Found {len(tables)} tables")
            
            # Check for NVR-related tables
            nvr_tables = [t for t in tables if 'nvr' in t.lower() or 'video' in t.lower()]
            if nvr_tables:
                print(f"   NVR-related tables: {', '.join(nvr_tables)}")
            
            return True
            
        except Exception as e:
            print(f"FAIL DynamoDB access failed: {e}")
            return False
    
    def test_lambda_access(self):
        """Test Lambda access"""
        print("\nTesting Lambda Access...")
        
        try:
            self.lambda_client = boto3.client('lambda')
            
            # List functions to test access
            response = self.lambda_client.list_functions()
            functions = [f['FunctionName'] for f in response['Functions']]
            
            print(f"PASS Lambda access successful")
            print(f"   Found {len(functions)} functions")
            
            # Check for NVR-related functions
            nvr_functions = [f for f in functions if 'nvr' in f.lower() or 'video' in f.lower()]
            if nvr_functions:
                print(f"   NVR-related functions: {', '.join(nvr_functions)}")
            
            return True
            
        except Exception as e:
            print(f"FAIL Lambda access failed: {e}")
            return False
    
    def test_s3_upload(self):
        """Test S3 upload capability"""
        print("\nTesting S3 Upload...")
        
        bucket_name = os.getenv('AWS_S3_BUCKET')
        if not bucket_name:
            print("   WARNING No S3 bucket configured (AWS_S3_BUCKET)")
            return False
        
        try:
            # Create test file content
            test_content = f"NVR System Test - {boto3.client('sts').get_caller_identity()['Account']}"
            test_key = "test/nvr-system-test.txt"
            
            # Upload test file
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=test_key,
                Body=test_content.encode('utf-8'),
                ContentType='text/plain'
            )
            
            print(f"PASS S3 upload successful")
            print(f"   Uploaded to: s3://{bucket_name}/{test_key}")
            
            # Clean up test file
            self.s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            print(f"   Test file cleaned up")
            
            return True
            
        except Exception as e:
            print(f"FAIL S3 upload failed: {e}")
            return False
    
    def test_environment_variables(self):
        """Test required environment variables"""
        print("\nTesting Environment Variables...")
        
        # Essential variables for the application
        essential_vars = ['AWS_REGION', 'AWS_S3_BUCKET']
        # Optional variables (can use AWS CLI instead)
        optional_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
        
        missing_essential = []
        missing_optional = []
        
        for var in essential_vars:
            value = os.getenv(var)
            if value:
                print(f"   PASS {var}: {'*' * (len(value) - 4) + value[-4:] if len(value) > 4 else '***'}")
            else:
                print(f"   FAIL {var}: Not set")
                missing_essential.append(var)
        
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                print(f"   PASS {var}: {'*' * (len(value) - 4) + value[-4:] if len(value) > 4 else '***'}")
            else:
                print(f"   WARNING {var}: Not set (using AWS CLI credentials)")
                missing_optional.append(var)
        
        if missing_essential:
            print(f"\nFAIL Missing essential environment variables: {', '.join(missing_essential)}")
            return False
        
        if missing_optional:
            print(f"\nUsing AWS CLI credentials instead of environment variables (recommended)")
            
        return True
        
        return True
    
    def run_quick_test(self):
        """Run quick AWS connectivity test"""
        print("Quick AWS Connectivity Test")
        print("=" * 40)
        
        results = {}
        
        # Test credentials
        results['credentials'] = self.test_credentials()
        
        # Test environment variables
        results['environment'] = self.test_environment_variables()
        
        # Test basic service access
        results['s3'] = self.test_s3_access()
        results['dynamodb'] = self.test_dynamodb_access()
        results['lambda'] = self.test_lambda_access()
        
        return results
    
    def run_full_test(self):
        """Run complete AWS setup test"""
        print("Complete AWS Setup Test")
        print("=" * 40)
        
        results = {}
        
        # Test credentials
        results['credentials'] = self.test_credentials()
        
        # Test environment variables
        results['environment'] = self.test_environment_variables()
        
        # Test service access
        results['s3'] = self.test_s3_access()
        results['dynamodb'] = self.test_dynamodb_access()
        results['lambda'] = self.test_lambda_access()
        
        # Test S3 upload
        if results['s3']:
            results['s3_upload'] = self.test_s3_upload()
        else:
            results['s3_upload'] = False
        
        # Summary
        print("\n" + "=" * 40)
        print("AWS Test Results:")
        
        passed = sum(1 for v in results.values() if v is True)
        failed = sum(1 for v in results.values() if v is False)
        
        print(f"   PASS Passed: {passed}")
        print(f"   FAIL Failed: {failed}")
        
        if failed == 0:
            print("\nPASS All AWS tests passed! System is ready.")
        else:
            print(f"\nFAIL {failed} tests failed. Check configuration.")
        
        return results

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test AWS setup for NVR system')
    parser.add_argument('--quick', action='store_true', help='Run quick test only')
    
    args = parser.parse_args()
    
    tester = AWSSetupTester()
    
    if args.quick:
        results = tester.run_quick_test()
    else:
        results = tester.run_full_test()
    
    # Exit with error code if any tests failed
    failed_count = sum(1 for v in results.values() if v is False)
    sys.exit(failed_count)

if __name__ == "__main__":
    sys.exit(main())