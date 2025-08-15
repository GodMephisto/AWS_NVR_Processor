# AWS Lambda Deployment Guide

## 🚀 Deploy Your Lambda Functions to AWS

### **Method 1: AWS Console (Easiest)**

#### **Step 1: Create Lambda Functions**

**1.1 Create Indexer Function:**
1. Go to AWS Lambda Console → Create Function
2. **Function name**: `nvr-video-indexer`
3. **Runtime**: Python 3.11
4. **Architecture**: x86_64
5. Click "Create function"

**1.2 Create Normalizer Function:**
1. Create Function → `nvr-video-normalizer`
2. **Runtime**: Python 3.11
3. **Architecture**: x86_64
4. Click "Create function"

#### **Step 2: Upload Code**

**2.1 Upload Indexer:**
1. Open `nvr-video-indexer` function
2. Go to "Code" tab
3. Delete default code
4. Copy entire content from `aws-lambda/lambda_indexer.py`
5. Paste into `lambda_function.py`
6. Change function name from `handler` to `lambda_handler`
7. Click "Deploy"

**2.2 Upload Normalizer:**
1. Open `nvr-video-normalizer` function
2. Go to "Code" tab
3. Copy entire content from `aws-lambda/lambda_normalizer.py`
4. Paste into `lambda_function.py`
5. Change function name from `handler` to `lambda_handler`
6. Click "Deploy"

#### **Step 3: Configure Environment Variables**

**3.1 Indexer Environment Variables:**
```
BUCKET = your-nvr-bucket-name
TABLE = nvr-video-index
LOG_LEVEL = INFO
```

**3.2 Normalizer Environment Variables:**
```
BUCKET = your-nvr-bucket-name
INDEXER_FUNCTION = nvr-video-indexer
LOG_LEVEL = INFO
```

#### **Step 4: Set Up S3 Triggers**

**4.1 Configure S3 Event:**
1. Go to S3 Console → Your bucket
2. Properties → Event notifications
3. Create event notification:
   - **Name**: `nvr-normalizer-trigger`
   - **Event types**: All object create events
   - **Destination**: Lambda function
   - **Lambda**: `nvr-video-normalizer`

---

### **Method 2: AWS CLI (Advanced)**

#### **Prerequisites:**
```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

#### **Deploy Script:**
```bash
# Create deployment package for indexer
cd aws-lambda
zip lambda_indexer.zip lambda_indexer.py

# Create indexer function
aws lambda create-function \
  --function-name nvr-video-indexer \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --handler lambda_indexer.lambda_handler \
  --zip-file fileb://lambda_indexer.zip \
  --environment Variables='{BUCKET=your-bucket,TABLE=nvr-video-index}'

# Create normalizer function
zip lambda_normalizer.zip lambda_normalizer.py

aws lambda create-function \
  --function-name nvr-video-normalizer \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --handler lambda_normalizer.lambda_handler \
  --zip-file fileb://lambda_normalizer.zip \
  --environment Variables='{BUCKET=your-bucket,INDEXER_FUNCTION=nvr-video-indexer}'
```

---

### **Method 3: One-Click Deployment Script**

I'll create an automated deployment script for you: