# AWS IoT Greengrass Migration Plan 🌐

## **When to Consider This Migration**

### **Triggers for Migration:**
- ✅ **20+ sites** deployed and operational
- ✅ **Manual management** becomes operational burden
- ✅ **Frequent software updates** needed across fleet
- ✅ **Compliance requirements** for managed infrastructure
- ✅ **Development team** has cloud-native expertise

### **Don't Migrate If:**
- ❌ **<10 sites** - Current system is more cost-effective
- ❌ **Limited development resources** - Migration takes 3-6 months
- ❌ **Budget constraints** - 3-5x cost increase
- ❌ **Simple requirements** - Current system meets all needs

---

## **🏗️ Migration Architecture**

### **Current System:**
```
📹 Camera → 🐍 Python NVR (test_main.py) → ☁️ AWS Services
```

### **Target Greengrass System:**
```
📹 Camera → 🖥️ Greengrass Core → λ Local Functions → ☁️ AWS Cloud
                    ↓
            ┌─────────────────────┐
            │  Greengrass Device  │
            ├─────────────────────┤
            │ λ camera_capture    │
            │ λ video_processor   │
            │ λ cloud_sync        │
            │ λ health_monitor    │
            │ 📊 Local DynamoDB   │
            │ 📁 Local Storage    │
            └─────────────────────┘
```

---

## **📦 Function Decomposition**

### **1. Camera Capture Lambda**
```python
# greengrass/functions/camera_capture/lambda_function.py
import json
import cv2
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """Capture video from cameras and trigger processing"""
    
    # Get camera configuration from local storage
    camera_config = get_camera_config()
    
    for camera in camera_config['cameras']:
        if camera['enabled']:
            # Capture video segment (5-10 minutes)
            video_path = capture_video_segment(camera)
            
            # Publish message to trigger processing
            publish_message('nvr/video/captured', {
                'camera_id': camera['id'],
                'video_path': video_path,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    return {'statusCode': 200, 'body': 'Capture completed'}

def capture_video_segment(camera):
    """Capture video from RTSP stream"""
    # Your existing camera capture logic
    pass

def publish_message(topic, payload):
    """Publish message to Greengrass message router"""
    # Greengrass local messaging
    pass
```

### **2. Video Processor Lambda**
```python
# greengrass/functions/video_processor/lambda_function.py
import json
from metadata_extractor import extract_metadata
from timelapse_processor import create_timelapse

def lambda_handler(event, context):
    """Process captured video files"""
    
    # Parse incoming message
    message = json.loads(event['Records'][0]['body'])
    video_path = message['video_path']
    camera_id = message['camera_id']
    
    # Extract metadata (your existing logic)
    metadata = extract_metadata(video_path)
    
    # Store metadata locally
    store_metadata_locally(camera_id, metadata)
    
    # Check if timelapse processing needed
    if should_create_timelapse(video_path):
        timelapse_path = create_timelapse(video_path)
        
        # Publish timelapse created message
        publish_message('nvr/timelapse/created', {
            'camera_id': camera_id,
            'timelapse_path': timelapse_path,
            'original_path': video_path
        })
    
    # Publish processing complete message
    publish_message('nvr/video/processed', {
        'camera_id': camera_id,
        'video_path': video_path,
        'metadata': metadata
    })
    
    return {'statusCode': 200, 'body': 'Processing completed'}
```

### **3. Cloud Sync Lambda**
```python
# greengrass/functions/cloud_sync/lambda_function.py
import json
import boto3
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """Sync processed videos to cloud storage"""
    
    # Parse incoming message
    message = json.loads(event['Records'][0]['body'])
    video_path = message['video_path']
    metadata = message['metadata']
    
    # Check connectivity to cloud
    if not check_cloud_connectivity():
        # Store for later sync
        queue_for_later_sync(message)
        return {'statusCode': 202, 'body': 'Queued for later sync'}
    
    try:
        # Upload to S3
        s3_key = upload_to_s3(video_path, metadata)
        
        # Update cloud DynamoDB
        update_cloud_index(metadata, s3_key)
        
        # Clean up local file if successful
        cleanup_local_file(video_path)
        
        return {'statusCode': 200, 'body': 'Sync completed'}
        
    except ClientError as e:
        # Handle sync failures
        handle_sync_failure(message, str(e))
        return {'statusCode': 500, 'body': f'Sync failed: {e}'}
```

### **4. Health Monitor Lambda**
```python
# greengrass/functions/health_monitor/lambda_function.py
import json
import psutil
import subprocess
from datetime import datetime

def lambda_handler(event, context):
    """Monitor system health and report to cloud"""
    
    health_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'camera_status': check_camera_connectivity(),
        'cloud_connectivity': check_cloud_connectivity(),
        'local_storage': get_local_storage_stats()
    }
    
    # Store locally
    store_health_data_locally(health_data)
    
    # Send to cloud if connected
    if health_data['cloud_connectivity']:
        send_health_to_cloud(health_data)
    
    # Check for alerts
    check_and_send_alerts(health_data)
    
    return {'statusCode': 200, 'body': 'Health check completed'}
```

---

## **⚙️ Greengrass Configuration**

### **Group Configuration:**
```json
{
  "GroupId": "nvr-system-group",
  "Name": "NVR System Group",
  "InitialVersion": {
    "CoreDefinitionVersionArn": "arn:aws:greengrass:region:account:cores/nvr-core",
    "FunctionDefinitionVersionArn": "arn:aws:greengrass:region:account:functions/nvr-functions",
    "SubscriptionDefinitionVersionArn": "arn:aws:greengrass:region:account:subscriptions/nvr-subscriptions",
    "ResourceDefinitionVersionArn": "arn:aws:greengrass:region:account:resources/nvr-resources"
  }
}
```

### **Function Configuration:**
```json
{
  "Functions": [
    {
      "Id": "camera-capture",
      "FunctionArn": "arn:aws:lambda:region:account:function:camera-capture",
      "FunctionConfiguration": {
        "Runtime": "python3.11",
        "Handler": "lambda_function.lambda_handler",
        "MemorySize": 512000,
        "Timeout": 300,
        "Environment": {
          "Variables": {
            "CAMERA_CONFIG_PATH": "/opt/nvr/config/cameras.json",
            "VIDEO_STORAGE_PATH": "/opt/nvr/storage/videos"
          }
        }
      }
    },
    {
      "Id": "video-processor",
      "FunctionArn": "arn:aws:lambda:region:account:function:video-processor",
      "FunctionConfiguration": {
        "Runtime": "python3.11",
        "Handler": "lambda_function.lambda_handler",
        "MemorySize": 1024000,
        "Timeout": 600
      }
    }
  ]
}
```

### **Subscription Configuration:**
```json
{
  "Subscriptions": [
    {
      "Id": "camera-to-processor",
      "Source": "arn:aws:lambda:region:account:function:camera-capture",
      "Target": "arn:aws:lambda:region:account:function:video-processor",
      "Subject": "nvr/video/captured"
    },
    {
      "Id": "processor-to-sync",
      "Source": "arn:aws:lambda:region:account:function:video-processor", 
      "Target": "arn:aws:lambda:region:account:function:cloud-sync",
      "Subject": "nvr/video/processed"
    },
    {
      "Id": "health-to-cloud",
      "Source": "arn:aws:lambda:region:account:function:health-monitor",
      "Target": "cloud",
      "Subject": "nvr/health/status"
    }
  ]
}
```

---

## **📋 Migration Steps**

### **Phase 1: Preparation (2-4 weeks)**
1. **Set up Greengrass development environment**
2. **Create Lambda functions** from existing code
3. **Test functions locally** with Greengrass SDK
4. **Create deployment packages** and test configurations

### **Phase 2: Pilot Deployment (2-3 weeks)**
1. **Deploy to 1-2 test sites**
2. **Monitor performance** and reliability
3. **Compare costs** with current system
4. **Gather operational feedback**

### **Phase 3: Gradual Migration (4-8 weeks)**
1. **Migrate 25% of sites** per week
2. **Monitor each batch** for issues
3. **Rollback capability** for failed migrations
4. **Update documentation** and procedures

### **Phase 4: Optimization (2-4 weeks)**
1. **Performance tuning** based on production data
2. **Cost optimization** - right-size resources
3. **Monitoring enhancement** - custom metrics
4. **Training** for operations team

---

## **💰 Cost Analysis**

### **Current System (10 sites):**
```
Monthly Cost: $50-100
├── S3 storage: $20-40
├── DynamoDB: $10-20
├── Lambda: $5-10
├── CloudFront: $10-20
└── Operational overhead: $5-10
```

### **Greengrass System (10 sites):**
```
Monthly Cost: $200-400
├── Greengrass device management: $16 × 10 = $160
├── Message routing: $20-40
├── S3 storage: $20-40
├── DynamoDB: $10-20
├── Lambda (cloud): $5-10
├── CloudFront: $10-20
└── Reduced operational overhead: -$30
```

### **Break-Even Analysis:**
- **Additional cost**: $150-300/month
- **Operational savings**: ~$50/month per site
- **Break-even point**: 20+ sites
- **ROI positive**: 30+ sites

---

## **⚠️ Migration Risks & Mitigation**

### **Technical Risks:**
1. **Lambda runtime limitations** (15-minute max)
   - **Mitigation**: Break long processes into smaller functions
2. **Local storage constraints**
   - **Mitigation**: Implement intelligent data retention
3. **Message routing complexity**
   - **Mitigation**: Extensive testing and monitoring
4. **Debugging difficulty**
   - **Mitigation**: Enhanced logging and local testing tools

### **Operational Risks:**
1. **Increased complexity**
   - **Mitigation**: Comprehensive training and documentation
2. **Vendor lock-in**
   - **Mitigation**: Maintain abstraction layers
3. **Cost escalation**
   - **Mitigation**: Regular cost monitoring and optimization
4. **Migration downtime**
   - **Mitigation**: Blue-green deployment strategy

---

## **🎯 Success Criteria**

### **Technical Success:**
- ✅ **99.9% uptime** maintained during migration
- ✅ **<10% performance degradation** vs current system
- ✅ **All existing features** working in Greengrass
- ✅ **Remote management** capabilities functional

### **Operational Success:**
- ✅ **50% reduction** in manual operations
- ✅ **Centralized monitoring** for all sites
- ✅ **Remote deployment** capabilities working
- ✅ **Team trained** on new architecture

### **Business Success:**
- ✅ **ROI positive** within 12 months
- ✅ **Customer satisfaction** maintained or improved
- ✅ **Scalability** to 100+ sites demonstrated
- ✅ **Competitive advantage** from advanced features

---

## **📞 Decision Framework**

### **Go/No-Go Criteria:**
```
✅ GO if:
├── 20+ sites committed for deployment
├── Development team has 6+ months capacity
├── Budget approved for 3-5x cost increase
├── Business case shows ROI within 18 months
└── Pilot deployment successful

❌ NO-GO if:
├── <10 sites in pipeline
├── Limited development resources
├── Cost increase not justified by benefits
├── Current system meeting all requirements
└── High-risk tolerance not acceptable
```

**Remember: Your current system is excellent for <20 sites. Only migrate when scale absolutely demands it!** 🎯