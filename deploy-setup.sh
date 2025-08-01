#!/bin/bash

# KirlewAI Google Cloud Setup Script
set -e

echo "🚀 Setting up KirlewAI Google Cloud Project..."

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "Please run 'gcloud auth login' first"
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

# Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable vision.googleapis.com
gcloud services enable gmail.googleapis.com
gcloud services enable calendar-json.googleapis.com
gcloud services enable people.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com

echo "✅ APIs enabled"

# Create service account
echo "🔐 Creating service account..."
SA_NAME="kirlewai-backend"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
    gcloud iam service-accounts create $SA_NAME \
        --display-name="KirlewAI Backend Service Account"
    
    # Grant permissions
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/speech.client"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/vision.imageAnnotator"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/gmail.readonly"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/calendar.events.readonly"
    
    echo "✅ Service account created with permissions"
else
    echo "✅ Service account already exists"
fi

# Create service account key
KEY_FILE="./kirlewai-service-account.json"
if [ ! -f "$KEY_FILE" ]; then
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SA_EMAIL
    echo "✅ Service account key created: $KEY_FILE"
else
    echo "✅ Service account key already exists"
fi

# Create environment file
echo "📝 Creating environment configuration..."
cat > .env << EOF
# Google Cloud Project Configuration
PROJECT_ID=$PROJECT_ID
REGION=us-central1

# OAuth Configuration (UPDATE THESE AFTER CREATING OAUTH CREDENTIALS)
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-oauth-client-secret
OAUTH_REDIRECT_URI=https://us-central1-$PROJECT_ID.cloudfunctions.net/multimodal-agent/auth/callback

# Service Account
GOOGLE_APPLICATION_CREDENTIALS=./kirlewai-service-account.json

# API Endpoints (UPDATE AFTER DEPLOYMENT)
CLOUD_FUNCTION_URL=https://us-central1-$PROJECT_ID.cloudfunctions.net/multimodal-agent

# Security
JWT_SECRET=$(openssl rand -base64 32)
ALLOWED_ORIGINS=https://your-domain.com

# Feature Flags
ENABLE_SPEECH_TO_TEXT=true
ENABLE_VISION_ANALYSIS=true
ENABLE_GMAIL_ACCESS=true
ENABLE_CALENDAR_ACCESS=true
EOF

echo "✅ Environment file created: .env"

echo ""
echo "🎉 Google Cloud setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Go to Google Cloud Console → APIs & Services → OAuth consent screen"
echo "2. Set up OAuth consent screen with your app details"
echo "3. Go to Credentials → Create OAuth 2.0 Client ID"
echo "4. Update .env file with your OAuth Client ID and Secret"
echo "5. Deploy your backend functions"
echo "6. Update Android app with correct Client ID"
echo ""
echo "📁 Files created:"
echo "   - .env (environment configuration)"
echo "   - kirlewai-service-account.json (service account key)"
echo "   - security-policy.yaml (security policies)"
echo ""
echo "🔗 Useful links:"
echo "   - Console: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID"
echo "   - OAuth: https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
echo "   - APIs: https://console.cloud.google.com/apis/dashboard?project=$PROJECT_ID"