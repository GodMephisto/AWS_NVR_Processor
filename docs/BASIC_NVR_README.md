# Basic NVR System for 4000H Testing

A simplified Network Video Recorder system designed for testing with Amcrest cameras on 4000H machines.

## Features

- **Amcrest Camera Support**: Optimized for Amcrest IP cameras
- **Basic Video Processing**: Simple metadata extraction and storage
- **AWS S3 Integration**: Optional cloud storage for videos
- **Web Interface**: Simple video viewing interface
- **Lightweight**: Minimal resource usage for testing environments

## Quick Setup

### 1. Run Setup Script
```bash
python3 setup_basic_nvr.py
```

This will:
- Create necessary directories
- Install Python dependencies
- Configure the system
- Set up systemd service

### 2. Test Camera Connection
```bash
python3 nvr-system/test_main.py --test-cameras
```

### 3. Start the System
```bash
python3 nvr-system/test_main.py
```

## Configuration

The system uses a simple JSON configuration file at `/opt/nvr/config/basic_config.json`:

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
    "bucket_name": "your-s3-bucket",
    "access_key_id": "your-access-key",
    "secret_access_key": "your-secret-key",
    "cloudfront_domain": ""
  },
  "storage": {
    "base_path": "/opt/nvr/storage",
    "max_usage_gb": 100,
    "retention_days": 3
  }
}
```

## Amcrest Camera Setup

### RTSP URL Format
```
rtsp://username:password@camera_ip:554/cam/realmonitor?channel=1&subtype=0
```

### Common Amcrest Settings
- **Default Username**: admin
- **Default Port**: 554 (RTSP)
- **Channel**: 1 (main stream), 2 (sub stream)
- **Subtype**: 0 (main), 1 (sub)

### Example URLs
- Main stream: `rtsp://admin:pass@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0`
- Sub stream: `rtsp://admin:pass@192.168.1.100:554/cam/realmonitor?channel=1&subtype=1`

## Testing Commands

### Test Camera Connection
```bash
python3 nvr-system/test_main.py --test-cameras
```

### Run with Debug Logging
```bash
python3 nvr-system/test_main.py --log-level DEBUG
```

### Check System Status
```bash
# If using systemd
sudo systemctl status basic-nvr

# Check logs
tail -f /opt/nvr/logs/basic_nvr.log
```

## Web Interface

Start the web interface:
```bash
python3 nvr-system/api/vod_api.py
```

Then open: http://localhost:8080

## Troubleshooting

### Camera Connection Issues
1. Check camera IP address and credentials
2. Verify RTSP URL format
3. Test with VLC media player first
4. Check network connectivity

### Storage Issues
1. Verify `/opt/nvr/storage` directory exists
2. Check disk space
3. Ensure proper permissions

### AWS Issues
1. Verify AWS credentials
2. Check S3 bucket permissions
3. Test with AWS CLI first

## File Structure

```
nvr-system/
├── config/
│   └── basic_config.py          # Configuration management
├── api/
│   └── vod_api.py              # Web API for video access
├── web/
│   └── index.html              # Simple web interface
├── services/
│   ├── metadata_extractor.py   # Video metadata extraction
│   ├── cloud_sync.py          # AWS S3 synchronization
│   └── vod_streaming.py       # Video streaming service
├── test_main.py               # Main application entry point
└── __init__.py
```

## System Requirements

- **OS**: Linux (tested on Ubuntu/CentOS)
- **Python**: 3.8+
- **Memory**: 2GB+ RAM
- **Storage**: 100GB+ available space
- **Network**: Stable connection to cameras and AWS (if used)

## Performance Notes

- Designed for 1-4 Amcrest cameras
- Optimized for 4000H series hardware
- Minimal CPU usage during normal operation
- Storage usage depends on video quality and retention settings

## Support

For issues specific to Amcrest cameras:
1. Check Amcrest documentation
2. Verify camera firmware version
3. Test RTSP stream with external tools
4. Check camera network settings