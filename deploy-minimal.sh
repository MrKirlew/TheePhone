#!/bin/bash

# KirlewAI Google Cloud Minimal Setup Script
set -e

echo "🚀 Setting up KirlewAI Google Cloud Project (Minimal Setup)..."

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Please run 'gcloud auth login' first"
    exit 1
fi

# Get or create project
read -p "Enter your project ID (or press Enter to create new): " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID="kirlewai-agent-$(date +%s)"
    echo "Creating new project: $PROJECT_ID"
    gcloud projects create $PROJECT_ID --name="KirlewAI Agent"
else
    echo "Using existing project: $PROJECT_ID"
fi

gcloud config set project $PROJECT_ID

echo "✅ Project configured: $PROJECT_ID"

# Enable essential APIs only
echo "🔧 Enabling essential APIs..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable vision.googleapis.com
gcloud services enable cloudbuild.googleapis.com

echo "✅ Essential APIs enabled"

# Create service account with minimal permissions
echo "🔐 Creating service account..."
SA_NAME="kirlewai-backend"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
    gcloud iam service-accounts create $SA_NAME \
        --display-name="KirlewAI Backend Service Account"
    
    # Grant only Cloud Functions invoker role (minimal)
    echo "Setting up minimal permissions..."
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/cloudfunctions.invoker"
    
    echo "✅ Service account created with minimal permissions"
else
    echo "✅ Service account already exists"
fi

# Create service account key
KEY_FILE="./kirlewai-service-account.json"
if [ ! -f "$KEY_FILE" ]; then
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SA_EMAIL
    echo "✅ Service account key created: $KEY_FILE"
    
    # Secure the key file
    chmod 600 $KEY_FILE
    echo "✅ Service account key secured"
else
    echo "✅ Service account key already exists"
fi

# Create environment file
echo "📝 Creating environment configuration..."
cat > .env << EOF
# Google Cloud Project Configuration
PROJECT_ID=$PROJECT_ID
REGION=us-central1

# OAuth Configuration (TO BE UPDATED)
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-oauth-client-secret

# Service Account  
GOOGLE_APPLICATION_CREDENTIALS=./kirlewai-service-account.json

# API Endpoints (TO BE UPDATED AFTER DEPLOYMENT)
CLOUD_FUNCTION_URL=https://us-central1-$PROJECT_ID.cloudfunctions.net/multimodal-agent

# Security
JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || echo "please-generate-random-secret")

# Feature Flags
ENABLE_SPEECH_TO_TEXT=true
ENABLE_VISION_ANALYSIS=true
ENABLE_GMAIL_ACCESS=false
ENABLE_CALENDAR_ACCESS=false
EOF

echo "✅ Environment file created: .env"

# Create a simple instruction file
cat > SETUP_INSTRUCTIONS.md << EOF
# KirlewAI Setup Instructions

## ✅ Completed
- Google Cloud project created: **$PROJECT_ID**
- Essential APIs enabled (Functions, Speech, Vision)
- Service account created with minimal permissions
- Environment configuration ready

## 📋 Manual Steps Required

### 1. Enable Additional APIs (Optional)
Go to: https://console.cloud.google.com/apis/library?project=$PROJECT_ID

Search for and enable:
- Gmail API (if you want email access)
- Google Calendar API (if you want calendar access)

### 2. Set up OAuth Consent Screen
1. Go to: https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID
2. Choose "External" for public app
3. Fill in required fields:
   - App name: KirlewAI Agent
   - User support email: your-email@domain.com
   - Developer contact: your-email@domain.com
4. Add scopes:
   - userinfo.email
   - userinfo.profile
   - gmail.readonly (if enabled)
   - calendar.readonly (if enabled)

### 3. Create OAuth Credentials
1. Go to: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. Application type: Web application
4. Name: KirlewAI Web Client
5. Authorized redirect URIs: 
   - https://us-central1-$PROJECT_ID.cloudfunctions.net/multimodal-agent/auth/callback
6. Download the JSON and note the Client ID

### 4. Update Configuration
Edit the .env file and replace:
- GOOGLE_CLIENT_ID with your OAuth Client ID
- GOOGLE_CLIENT_SECRET with your OAuth Client Secret

### 5. Update Android App
In MainActivity.kt, replace:
- WEB_CLIENT_ID with your OAuth Client ID
- CLOUD_FUNCTION_URL with your Cloud Function URL

## 🔗 Quick Links
- Console: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID
- APIs: https://console.cloud.google.com/apis/dashboard?project=$PROJECT_ID
- Credentials: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID

EOF

echo ""
echo "🎉 Minimal Google Cloud setup complete!"
echo ""
echo "📁 Files created:"
echo "   - .env (environment configuration)"
echo "   - kirlewai-service-account.json (service account key - keep secure!)"
echo "   - SETUP_INSTRUCTIONS.md (next steps guide)"
echo ""
echo "📋 Next: Follow the instructions in SETUP_INSTRUCTIONS.md"
echo "🔗 Project Console: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID"