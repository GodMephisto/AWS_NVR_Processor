#!/usr/bin/env python3
"""
AWS Lambda Video Normalizer
Organizes video files and triggers indexing
"""

import json
import boto3
import os
from urllib.parse import unquote_plus

# Initialize AWS clients
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """Lambda handler for video normalization"""
    
    try:
        # Get environment variables
        bucket = os.environ.get('BUCKET')
        indexer_function = os.environ.get('INDEXER_FUNCTION', 'nvr-video-indexer')
        
        # Process each S3 record
        results = []
        
        for record in event.get('Records', []):
            try:
                # Extract S3 information
                source_bucket = record['s3']['bucket']['name']
                source_key = unquote_plus(record['s3']['object']['key'])
                
                print(f"Processing file: {source_key}")
                
                # Normalize the file path if needed
                normalized_key = normalize_video_path(source_key)
                
                # If path changed, copy to normalized location
                if normalized_key != source_key:
                    copy_source = {'Bucket': source_bucket, 'Key': source_key}
                    s3_client.copy_object(
                        CopySource=copy_source,
                        Bucket=source_bucket,
                        Key=normalized_key
                    )
                    
                    # Delete original if it was moved
                    s3_client.delete_object(Bucket=source_bucket, Key=source_key)
                    
                    print(f"Normalized: {source_key} -> {normalized_key}")
                    final_key = normalized_key
                else:
                    final_key = source_key
                
                # Trigger indexer function
                indexer_payload = {
                    'Records': [{
                        's3': {
                            'bucket': {'name': source_bucket},
                            'object': {
                                'key': final_key,
                                'size': record['s3']['object']['size']
                            }
                        }
                    }]
                }
                
                lambda_client.invoke(
                    FunctionName=indexer_function,
                    InvocationType='Event',  # Async
                    Payload=json.dumps(indexer_payload)
                )
                
                results.append({
                    'original_key': source_key,
                    'final_key': final_key,
                    'status': 'success',
                    'normalized': normalized_key != source_key
                })
                
            except Exception as e:
                print(f"Error processing record: {e}")
                results.append({
                    'key': record.get('s3', {}).get('object', {}).get('key', 'unknown'),
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(results)} files',
                'results': results
            })
        }
        
    except Exception as e:
        print(f"Lambda error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def normalize_video_path(s3_key):
    """Normalize video file path to standard format"""
    
    # Target format: videos/site_id/camera_id/YYYYMMDD/filename
    
    # If already in correct format, return as-is
    if s3_key.startswith('videos/') and s3_key.count('/') >= 4:
        return s3_key
    
    # Extract filename
    filename = s3_key.split('/')[-1]
    
    # Try to parse Amcrest filename format: YYYYMMDD_HHMMSS_camera_id_sequence.dav
    try:
        if '_' in filename and '.' in filename:
            parts = filename.split('_')
            if len(parts) >= 3:
                date_part = parts[0]  # YYYYMMDD
                camera_id = parts[2] if len(parts) > 2 else 'unknown'
                
                # Default site_id
                site_id = 'default_site'
                
                # Construct normalized path
                normalized_path = f"videos/{site_id}/{camera_id}/{date_part}/{filename}"
                return normalized_path
    
    except Exception as e:
        print(f"Error normalizing path {s3_key}: {e}")
    
    # Fallback: put in default location
    return f"videos/unknown/unknown/unknown/{filename}"