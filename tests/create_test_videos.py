#!/usr/bin/env python3
"""
Create Test Videos for VOD System
Generates realistic test video files for system testing
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

class TestVideoCreator:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.test_videos_path = self.base_path / "test_videos"
        
    def create_test_video_file(self, file_path, size_kb=100):
        """Create a mock video file"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a simple mock video file
        with open(file_path, 'wb') as f:
            # Write some mock video data
            f.write(b'MOCK_VIDEO_DATA' * (size_kb * 1024 // 15))
        
        return file_path
    
    def generate_test_structure(self):
        """Generate realistic test video structure"""
        print("Creating Test Videos for VOD System")
        print("=" * 40)
        
        # Define test cameras
        cameras = ['amcrest_001', 'amcrest_002']
        site_id = 'test_site'
        
        # Generate videos for last 3 days
        base_date = datetime.now()
        video_files = []
        metadata = []
        
        for days_back in range(3):
            current_date = base_date - timedelta(days=days_back)
            date_str = current_date.strftime('%Y%m%d')
            
            for camera in cameras:
                # Create directory structure: site/camera/date/
                video_dir = self.test_videos_path / site_id / camera / date_str
                
                # Generate 3 videos per day per camera
                for hour in [8, 14, 20]:  # 8am, 2pm, 8pm
                    timestamp = f"{date_str}_{hour:02d}0000"
                    filename = f"{timestamp}_{camera}_001.dav"
                    
                    video_path = video_dir / filename
                    self.create_test_video_file(video_path, size_kb=500)
                    
                    video_files.append(str(video_path.relative_to(self.base_path)))
                    
                    # Create metadata
                    metadata.append({
                        'filename': filename,
                        'camera_id': camera,
                        'site_id': site_id,
                        'timestamp': current_date.replace(hour=hour, minute=0, second=0).isoformat(),
                        'date': date_str,
                        'size': 500 * 1024,
                        'duration': 300,  # 5 minutes
                        'path': str(video_path.relative_to(self.base_path))
                    })
                    
                    print(f"Created test video: {video_path.relative_to(self.base_path)}")
        
        # Save metadata
        metadata_file = self.test_videos_path / "test_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create test environment file
        env_test_file = self.base_path / ".env.test"
        with open(env_test_file, 'w') as f:
            f.write("# Test Environment Configuration\n")
            f.write("AWS_REGION=us-east-1\n")
            f.write("AWS_S3_BUCKET=test-nvr-bucket\n")
            f.write("DYNAMODB_TABLE=test-nvr-video-index\n")
            f.write("# Update AWS credentials before testing!\n")
        
        print(f"\nPASS Created {len(video_files)} test video files")
        print(f"Base directory: {self.test_videos_path}")
        print(f"Metadata saved to: {metadata_file.relative_to(self.base_path)}")
        print(f"Test config created: {env_test_file.relative_to(self.base_path)}")
        print("   Update AWS credentials before testing!")
        
        print(f"\nNext Steps:")
        print("1. Update .env.test with your AWS credentials")
        print("2. Upload test videos: python nvr-system/services/cloud_sync.py --source test_videos")
        print("3. Start VOD API: python src/nvr_vod_server.py")
        print("4. Run tests: python tests/test_vod_streaming.py")
        
        return video_files, metadata

def main():
    """Main function"""
    creator = TestVideoCreator()
    
    try:
        video_files, metadata = creator.generate_test_structure()
        print(f"\nSUCCESS: Created {len(video_files)} test videos")
        return True
    except Exception as e:
        print(f"ERROR: Failed to create test videos: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)