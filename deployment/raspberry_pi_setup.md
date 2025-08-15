# Raspberry Pi NVR System Setup
Complete guide for running your NVR system on Raspberry Pi

## 🎯 Why Raspberry Pi is Perfect

### Advantages:
- **Always-on operation** - 24/7 without heating up
- **Low power consumption** - ~5W vs 50-100W laptop
- **Dedicated device** - Won't interfere with other work
- **Headless operation** - No monitor needed after setup
- **Cost effective** - $75 total cost
- **Silent operation** - No fans

### Performance:
- **Raspberry Pi 4 (8GB)** - Handles 4-8 cameras easily
- **Video processing** - Metadata extraction, motion detection
- **Cloud uploads** - Concurrent S3 uploads
- **VOD streaming** - Serves 5-10 concurrent streams

## 🛒 Hardware Requirements

### Essential Components:
- **Raspberry Pi 4 (8GB RAM)** - $75
- **MicroSD Card (64GB+)** - $15
- **Power Supply (USB-C)** - $10
- **Ethernet Cable** - $5
- **Case with cooling** - $15

### Optional:
- **External SSD** - For local video cache
- **PoE HAT** - Power over Ethernet

**Total Cost: ~$120**

## 🔧 Installation Steps

### Step 1: Prepare SD Card
```bash
# Download Raspberry Pi Imager
# Flash Raspberry Pi OS Lite (64-bit)
# Enable SSH in advanced options
# Set username: nvr, password: your_choice
```

### Step 2: Initial Setup
```bash
# SSH into Pi
ssh nvr@192.168.1.200

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv git -y

# Install system dependencies
sudo apt install ffmpeg libopencv-dev python3-opencv -y
```

### Step 3: Install Your NVR System
```bash
# Clone your project
git clone https://github.com/your-repo/nvr-system.git
cd nvr-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install flask boto3 opencv-python requests python-dotenv

# Make scripts executable
chmod +x src/nvr_vod_server.py
chmod +x src/nvr_system_manager.py
chmod +x tools/nvr_connection_tester.py
```

### Step 4: Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Add your settings:
NVR_HOST=192.168.1.100
NVR_STORAGE_PATH=//192.168.1.100/VideoStorage
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-nvr-bucket
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### Step 5: Test Connection
```bash
# Test NVR discovery
python3 tools/nvr_connection_tester.py --auto-discover

# Test VOD server
python3 src/nvr_vod_server.py --host 0.0.0.0 --port 8080
```

## 🚀 Auto-Start Configuration

### Create Systemd Service:
```bash
# Create service file
sudo nano /etc/systemd/system/nvr-system.service
```

```ini
[Unit]
Description=NVR Video Processing System
After=network.target

[Service]
Type=simple
User=nvr
WorkingDirectory=/home/nvr/nvr-system
Environment=PATH=/home/nvr/nvr-system/venv/bin
ExecStart=/home/nvr/nvr-system/venv/bin/python src/nvr_system_manager.py --start-all --nvr-path "//192.168.1.100/VideoStorage"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable Auto-Start:
```bash
# Enable service
sudo systemctl enable nvr-system.service

# Start service
sudo systemctl start nvr-system.service

# Check status
sudo systemctl status nvr-system.service
```

## 📊 Performance Optimization

### Memory Optimization:
```bash
# Increase GPU memory split
sudo nano /boot/config.txt

# Add these lines:
gpu_mem=128
dtoverlay=vc4-kms-v3d
max_framebuffers=2
```

### Network Optimization:
```bash
# Optimize network buffer sizes
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
```

### Storage Optimization:
```bash
# Mount external SSD for video cache
sudo mkdir /mnt/video-cache
sudo mount /dev/sda1 /mnt/video-cache

# Add to fstab for auto-mount
echo '/dev/sda1 /mnt/video-cache ext4 defaults 0 2' | sudo tee -a /etc/fstab
```

## 🌐 Remote Access Setup

### SSH Access:
```bash
# Generate SSH key for secure access
ssh-keygen -t rsa -b 4096

# Copy public key to Pi
ssh-copy-id nvr@192.168.1.200
```

### Web Interface Access:
```bash
# Access VOD API from any device
http://192.168.1.200:8080/api/v1/health
http://192.168.1.200:8080/api/v1/videos/search
```

### VPN Access (Optional):
```bash
# Install WireGuard for secure remote access
sudo apt install wireguard -y

# Configure VPN server
# (Detailed VPN setup guide available separately)
```

## 🔍 Monitoring and Maintenance

### System Monitoring:
```bash
# Check system resources
htop

# Check service logs
sudo journalctl -u nvr-system.service -f

# Check disk usage
df -h

# Check network connections
netstat -tulpn | grep :8080
```

### Maintenance Scripts:
```bash
# Create maintenance script
nano ~/maintenance.sh
```

```bash
#!/bin/bash
# NVR System Maintenance

echo "🔧 NVR System Maintenance - $(date)"

# Check disk space
echo "💾 Disk Usage:"
df -h

# Check service status
echo "🚀 Service Status:"
sudo systemctl status nvr-system.service --no-pager

# Check recent logs
echo "📋 Recent Logs:"
sudo journalctl -u nvr-system.service --since "1 hour ago" --no-pager

# Update system
echo "📦 System Updates:"
sudo apt update && sudo apt list --upgradable

echo "✅ Maintenance Complete"
```

## 🎯 Raspberry Pi vs Laptop Comparison

| Feature | Raspberry Pi 4 | Laptop |
|---------|----------------|---------|
| **Cost** | $120 | $800+ |
| **Power** | 5W | 50-100W |
| **Always-on** | Perfect | Uses main computer |
| **Performance** | Good for 4-8 cameras | Excellent |
| **Setup** | Dedicated device | Shared device |
| **Maintenance** | Minimal | Regular updates |
| **Portability** | Fixed installation | Mobile |

## 🚀 Thursday Setup with Raspberry Pi

### Quick Setup (30 minutes):
1. **Flash SD card** with pre-configured image
2. **Boot Raspberry Pi** and SSH in
3. **Run auto-discovery** to find NVR
4. **Start NVR system** service
5. **Access from phone** via web interface

### Commands:
```bash
# SSH into Pi
ssh nvr@192.168.1.200

# Auto-discover NVR
python3 tools/nvr_connection_tester.py --auto-discover

# Start system
sudo systemctl start nvr-system.service

# Check status
curl http://192.168.1.200:8080/api/v1/health
```

## 💡 Why Raspberry Pi is Actually Better

### For Your Use Case:
- **Dedicated device** - Won't slow down your laptop
- **Always available** - 24/7 operation without thinking about it
- **Lower power** - Runs for pennies per month
- **Silent operation** - No fan noise
- **Professional setup** - Like enterprise systems
- **Expandable** - Add more Pis for more cameras

### Enterprise Advantage:
- **Scalable** - One Pi per site/building
- **Reliable** - Industrial-grade operation
- **Maintainable** - Remote updates and monitoring
- **Cost-effective** - $120 vs $2000+ commercial solutions

**Raspberry Pi is actually the PERFECT platform for your NVR system!** 🎯

**It's what professional installers would use!** 🏆