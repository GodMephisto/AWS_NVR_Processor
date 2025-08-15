#!/usr/bin/env python3
"""
AWS Lambda Video Indexer
Processes video metadata and stores in DynamoDB
"""

import json
import boto3
import os
from datetime import datetime
from urllib.parse import unquote_plus

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """Lambda handler for video indexing"""
    
    try:
        # Get environment variables
        table_name = os.environ.get('TABLE', 'nvr-video-index')
        table = dynamodb.Table(table_name)
        
        # Process each record
        results = []
        
        for record in event.get('Records', []):
            try:
                # Extract S3 information
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                size = record['s3']['object']['size']
                
                # Parse video metadata from filename/path
                metadata = parse_video_metadata(key, size)
                
                # Store in DynamoDB
                response = table.put_item(Item=metadata)
                
                results.append({
                    'key': key,
                    'status': 'success',
                    'metadata': metadata
                })
                
                print(f"Indexed video: {key}")
                
            except Exception as e:
                print(f"Error processing record {record}: {e}")
                results.append({
                    'key': record.get('s3', {}).get('object', {}).get('key', 'unknown'),
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(results)} records',
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

def parse_video_metadata(s3_key, file_size):
    """Parse video metadata from S3 key"""
    
    # Example key: videos/site_id/camera_id/YYYYMMDD/YYYYMMDD_HHMMSS_camera_id_sequence.dav
    parts = s3_key.split('/')
    
    metadata = {
        'video_id': s3_key,
        's3_key': s3_key,
        'file_size': file_size,
        'indexed_at': datetime.utcnow().isoformat(),
        'status': 'indexed'
    }
    
    try:
        if len(parts) >= 4:
            # Extract site_id, camera_id, date from path
            metadata['site_id'] = parts[1] if len(parts) > 1 else 'unknown'
            metadata['camera_id'] = parts[2] if len(parts) > 2 else 'unknown'
            metadata['date'] = parts[3] if len(parts) > 3 else 'unknown'
            
            # Extract timestamp from filename
            filename = parts[-1]
            if '_' in filename:
                timestamp_part = filename.split('_')[1]  # HHMMSS
                date_part = parts[3]  # YYYYMMDD
                
                if len(timestamp_part) == 6 and len(date_part) == 8:
                    # Construct full timestamp
                    full_timestamp = f"{date_part}_{timestamp_part}"
                    metadata['timestamp'] = full_timestamp
                    
                    # Convert to ISO format
                    try:
                        dt = datetime.strptime(full_timestamp, '%Y%m%d_%H%M%S')
                        metadata['iso_timestamp'] = dt.isoformat()
                    except ValueError:
                        pass
        
        # Add file extension
        if '.' in s3_key:
            metadata['file_extension'] = s3_key.split('.')[-1].lower()
        
    except Exception as e:
        print(f"Error parsing metadata for {s3_key}: {e}")
        # Continue with basic metadata
    
    return metadata