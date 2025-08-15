#!/usr/bin/env python3
"""
Automated AWS Lambda Deployment Script
Deploys NVR Lambda functions to AWS with proper configuration
"""

import boto3
import json
import os
import sys
import zipfile
from pathlib import Path
import time

class AWSLambdaDeployer:
    def __init__(self):
        self.lambda_client = boto3.client('lambda')
        self.s3_client = boto3.client('s3')
        self.iam_client = boto3.client('iam')
        
        # Load .env file first
        self._load_env_file()
        
        # Configuration
        self.bucket_name = os.getenv('S3_BUCKET') or input("Enter S3 bucket name: ").strip()
        self.table_name = os.getenv('DYNAMODB_TABLE', 'nvr-video-index')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        print(f"Deploying to bucket: {self.bucket_name}")
        print(f"DynamoDB table: {self.table_name}")
        print(f"Region: {self.aws_region}")
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        from pathlib import Path
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key and value and key not in os.environ:
                            os.environ[key] = value
    
    def create_lambda_role(self):
        """Create IAM role for Lambda functions"""
        role_name = 'nvr-lambda-execution-role'
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            # Try to get existing role
            response = self.iam_client.get_role(RoleName=role_name)
            role_arn = response['Role']['Arn']
            print(f"Using existing IAM role: {role_arn}")
            return role_arn
        except self.iam_client.exceptions.NoSuchEntityException:
            pass
        
        try:
            # Create new role
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description='Execution role for NVR Lambda functions'
            )
            role_arn = response['Role']['Arn']
            
            # Attach basic execution policy
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
            # Create and attach custom policy for S3 and DynamoDB
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                            "s3:HeadObject",
                            "s3:CopyObject"
                        ],
                        "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:PutItem",
                            "dynamodb:GetItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:Query",
                            "dynamodb:Scan"
                        ],
                        "Resource": f"arn:aws:dynamodb:{self.aws_region}:*:table/{self.table_name}"
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "lambda:InvokeFunction"
                        ],
                        "Resource": "*"
                    }
                ]
            }
            
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName='nvr-lambda-policy',
                PolicyDocument=json.dumps(policy_document)
            )
            
            print(f"Created IAM role: {role_arn}")
            
            # Wait for role to be available
            print("Waiting for IAM role to be ready...")
            time.sleep(10)
            
            return role_arn
            
        except Exception as e:
            print(f"Failed to create IAM role: {e}")
            sys.exit(1)
    
    def create_deployment_package(self, function_file, output_file):
        """Create deployment ZIP package"""
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Read the function file and modify handler name
            with open(function_file, 'r') as f:
                content = f.read()
            
            # Replace 'def handler(' with 'def lambda_handler('
            content = content.replace('def handler(', 'def lambda_handler(')
            
            # Write to lambda_function.py in zip
            zipf.writestr('lambda_function.py', content)
        
        print(f"Created deployment package: {output_file}")
    
    def deploy_function(self, function_name, zip_file, environment_vars, description):
        """Deploy or update Lambda function"""
        try:
            # Try to get existing function
            self.lambda_client.get_function(FunctionName=function_name)
            
            # Update existing function
            with open(zip_file, 'rb') as f:
                zip_content = f.read()
            
            self.lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            
            self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={'Variables': environment_vars}
            )
            
            print(f"Updated existing function: {function_name}")
            
        except self.lambda_client.exceptions.ResourceNotFoundException:
            # Create new function
            role_arn = self.create_lambda_role()
            
            with open(zip_file, 'rb') as f:
                zip_content = f.read()
            
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.11',
                Role=role_arn,
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description=description,
                Timeout=300,  # 5 minutes
                MemorySize=512,  # 512 MB
                Environment={'Variables': environment_vars}
            )
            
            print(f"Created new function: {function_name}")
            return response['FunctionArn']
    
    def setup_s3_trigger(self, function_name):
        """Set up S3 trigger for normalizer function"""
        try:
            # Add permission for S3 to invoke Lambda
            self.lambda_client.add_permission(
                FunctionName=function_name,
                StatementId='s3-trigger-permission',
                Action='lambda:InvokeFunction',
                Principal='s3.amazonaws.com',
                SourceArn=f'arn:aws:s3:::{self.bucket_name}'
            )
            
            # Configure S3 notification
            notification_config = {
                'LambdaConfigurations': [
                    {
                        'Id': 'nvr-normalizer-trigger',
                        'LambdaFunctionArn': f'arn:aws:lambda:{self.aws_region}:*:function:{function_name}',
                        'Events': ['s3:ObjectCreated:*']
                    }
                ]
            }
            
            self.s3_client.put_bucket_notification_configuration(
                Bucket=self.bucket_name,
                NotificationConfiguration=notification_config
            )
            
            print(f"Configured S3 trigger for {function_name}")
            
        except Exception as e:
            print(f"Warning: Could not set up S3 trigger: {e}")
            print("You may need to configure this manually in the AWS Console")
    
    def deploy_all(self):
        """Deploy both Lambda functions"""
        print("Starting AWS Lambda deployment...")
        
        # Deploy indexer function
        print("\n1. Deploying Indexer Function...")
        self.create_deployment_package('aws-lambda/lambda_indexer.py', 'lambda_indexer.zip')
        
        indexer_env = {
            'BUCKET': self.bucket_name,
            'TABLE': self.table_name,
            'LOG_LEVEL': 'INFO'
        }
        
        self.deploy_function(
            'nvr-video-indexer',
            'lambda_indexer.zip',
            indexer_env,
            'NVR Video Indexer - Processes video metadata and stores in DynamoDB'
        )
        
        # Deploy normalizer function
        print("\n2. Deploying Normalizer Function...")
        self.create_deployment_package('aws-lambda/lambda_normalizer.py', 'lambda_normalizer.zip')
        
        normalizer_env = {
            'BUCKET': self.bucket_name,
            'INDEXER_FUNCTION': 'nvr-video-indexer',
            'LOG_LEVEL': 'INFO'
        }
        
        self.deploy_function(
            'nvr-video-normalizer',
            'lambda_normalizer.zip',
            normalizer_env,
            'NVR Video Normalizer - Organizes video files and triggers indexing'
        )
        
        # Set up S3 trigger
        print("\n3. Setting up S3 Trigger...")
        self.setup_s3_trigger('nvr-video-normalizer')
        
        # Cleanup
        os.remove('lambda_indexer.zip')
        os.remove('lambda_normalizer.zip')
        
        print("\nDeployment completed successfully!")
        print("\nNext steps:")
        print("1. Test the functions in AWS Lambda Console")
        print("2. Upload a test video to S3 to verify the pipeline")
        print("3. Check CloudWatch logs for any issues")

def main():
    """Main deployment function"""
    print("NVR Lambda Function Deployment")
    print("=" * 40)
    
    # Check if aws-lambda directory exists
    if not Path('aws-lambda').exists():
        print("Error: aws-lambda directory not found!")
        print("Make sure you're running this from the project root directory")
        sys.exit(1)
    
    # Check AWS credentials
    try:
        boto3.client('sts').get_caller_identity()
        print("AWS credentials configured")
    except Exception as e:
        print(f"AWS credentials not configured: {e}")
        print("Run 'aws configure' first")
        sys.exit(1)
    
    # Deploy functions
    deployer = AWSLambdaDeployer()
    deployer.deploy_all()

if __name__ == "__main__":
    main()