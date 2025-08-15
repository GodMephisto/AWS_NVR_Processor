# NVR Connection Guide
Complete guide for connecting your system to the Amcrest NVR

## 🎯 Overview

Your system connects to the NVR in multiple ways:
1. **Network File Access** - Read video files from NVR storage
2. **RTSP Streaming** - Live camera feeds (optional)
3. **API Integration** - Camera control and status
4. **FTP/SMB Shares** - Automated file transfer

## 🔌 Connection Methods

### Method 1: Network File Share (Recommended)
**Best for: Accessing recorded video files**

#### Windows SMB Share:
```bash
# Mount NVR storage as network drive
net use Z: \\192.168.1.100\VideoStorage /persistent:yes

# Or access directly via UNC path
\\192.168.1.100\VideoStorage\Camera01\2024\01\15\
```

#### Configuration:
```python
# In your .env file
NVR_STORAGE_PATH=\\\\192.168.1.100\\VideoStorage
# or
NVR_STORAGE_PATH=Z:\\VideoStorage
```

### Method 2: FTP Access
**Best for: Automated file retrieval**

#### FTP Configuration:
```python
# In your .env file
NVR_FTP_HOST=192.168.1.100
NVR_FTP_PORT=21
NVR_FTP_USER=admin
NVR_FTP_PASS=your_password
NVR_FTP_PATH=/VideoStorage
```

### Method 3: RTSP Streaming
**Best for: Live camera feeds**

#### RTSP URLs:
```python
# Amcrest RTSP format
rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0

# In your .env file
CAMERA_001_RTSP_URL=rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0
CAMERA_002_RTSP_URL=rtsp://admin:password@192.168.1.102:554/cam/realmonitor?channel=1&subtype=0
```

## 🏠 Network Setup

### 1. Find Your NVR IP Address
```bash
# Windows - scan network
arp -a | findstr "192.168"

# Or use Amcrest IP Config Tool
# Download from Amcrest website
```

### 2. Configure NVR Network Settings
1. **Access NVR Web Interface:**
   - Open browser: `http://192.168.1.100` (your NVR IP)
   - Login: admin / your_password

2. **Enable Network Services:**
   - Enable SMB/CIFS file sharing
   - Enable FTP server (if needed)
   - Configure user permissions

3. **Set Static IP (Recommended):**
   - Network → TCP/IP
   - Set static IP: `192.168.1.100`
   - Gateway: `192.168.1.1`
   - DNS: `8.8.8.8`

### 3. Configure Camera IPs
```
NVR:      192.168.1.100
Camera 1: 192.168.1.101
Camera 2: 192.168.1.102
Your PC:  192.168.1.50
```

## 📁 File Structure Understanding

### Typical Amcrest NVR Structure:
```
\\NVR-IP\VideoStorage\
├── Camera01\
│   ├── 2024\
│   │   ├── 01\
│   │   │   ├── 15\
│   │   │   │   ├── 001\
│   │   │   │   │   ├── 20240115080000001.dav
│   │   │   │   │   ├── 20240115080500001.dav
│   │   │   │   │   └── ...
├── Camera02\
│   └── ...
```

### Your System Expects:
```
site_id/camera_id/YYYY/MM/DD/YYYYMMDD_HHMMSS_camera_id_sequence.dav
```

## 🔧 Configuration Files

### Update .env File:
```bash
# NVR Connection
NVR_HOST=192.168.1.100
NVR_STORAGE_PATH=\\\\192.168.1.100\\VideoStorage
NVR_USERNAME=admin
NVR_PASSWORD=your_nvr_password

# Camera Configuration
CAMERA_amcrest_001_IP=192.168.1.101
CAMERA_amcrest_001_RTSP=rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0
CAMERA_amcrest_001_SITE_ID=home
CAMERA_amcrest_001_ENABLED=true

CAMERA_amcrest_002_IP=192.168.1.102
CAMERA_amcrest_002_RTSP=rtsp://admin:password@192.168.1.102:554/cam/realmonitor?channel=1&subtype=0
CAMERA_amcrest_002_SITE_ID=home
CAMERA_amcrest_002_ENABLED=true

# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-nvr-bucket
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

## 🚀 Connection Testing

### Test Network Connectivity:
```bash
# Ping NVR
ping 192.168.1.100

# Test SMB share
dir \\192.168.1.100\VideoStorage

# Test FTP (if enabled)
ftp 192.168.1.100
```

### Test with Your System:
```bash
# Test file access
python src/nvr_system_manager.py --interactive
# Choose option 2: Start Cloud Sync
# Enter NVR path: \\192.168.1.100\VideoStorage
```

## 🔍 Troubleshooting

### Common Issues:

#### 1. "Access Denied" Error
**Solution:**
- Check NVR user permissions
- Enable guest access temporarily
- Use correct username/password

#### 2. "Network Path Not Found"
**Solution:**
- Verify NVR IP address
- Check network connectivity
- Enable SMB/CIFS on NVR

#### 3. "No Video Files Found"
**Solution:**
- Check file path structure
- Verify recording is enabled
- Check file permissions

#### 4. RTSP Connection Failed
**Solution:**
- Verify RTSP URL format
- Check camera IP addresses
- Test with VLC media player first

### Debug Commands:
```bash
# Test SMB connection
net use \\192.168.1.100\VideoStorage /user:admin password

# List available shares
net view \\192.168.1.100

# Test RTSP with VLC
vlc rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0
```

## 📋 Thursday Setup Checklist

### Pre-Setup (Before Hardware Arrives):
- [ ] Plan IP address scheme
- [ ] Prepare network cables
- [ ] Update .env configuration
- [ ] Test AWS connectivity

### Hardware Setup (15 minutes):
1. [ ] Connect NVR to network
2. [ ] Connect cameras to NVR/network
3. [ ] Power on all devices
4. [ ] Note IP addresses

### Software Configuration (10 minutes):
1. [ ] Access NVR web interface
2. [ ] Enable file sharing
3. [ ] Test network connectivity
4. [ ] Update system configuration

### System Integration (5 minutes):
1. [ ] Start NVR system manager
2. [ ] Test file access
3. [ ] Start cloud sync
4. [ ] Verify video processing

## 🎯 Quick Start Commands

### Once Hardware is Connected:
```bash
# 1. Find NVR IP
arp -a | findstr "192.168"

# 2. Test connection
ping 192.168.1.100
dir \\192.168.1.100\VideoStorage

# 3. Update .env with correct IPs
# Edit .env file with actual IP addresses

# 4. Start your system
python src/nvr_system_manager.py --start-all --nvr-path "\\192.168.1.100\VideoStorage"
```

## 🌐 Remote Access Setup

### For Remote Monitoring:
1. **Port Forwarding on Router:**
   - Forward port 8080 → Your PC IP
   - Forward port 80 → NVR IP (web interface)

2. **Dynamic DNS (Optional):**
   - Use service like No-IP or DuckDNS
   - Access via: `your-domain.ddns.net:8080`

3. **VPN Access (Recommended):**
   - Set up VPN server on router
   - Secure remote access to entire network

Your system will be ready to connect to any standard NVR setup! 🚀