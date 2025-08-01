#!/bin/bash

# KirlewAI Google Cloud Setup Script (Safe Version)
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

# Function to safely enable API
enable_api() {
    local api=$1
    echo "Enabling $api..."
    if gcloud services enable $api 2>/dev/null; then
        echo "✅ $api enabled"
    else
        echo "⚠️  $api failed to enable (may not exist or require different permissions)"
    fi
}

# Enable APIs safely
echo "🔧 Enabling required APIs..."
enable_api "cloudfunctions.googleapis.com"
enable_api "run.googleapis.com"
enable_api "speech.googleapis.com"
enable_api "vision.googleapis.com"
enable_api "cloudbuild.googleapis.com"
enable_api "iam.googleapis.com"
enable_api "cloudresourcemanager.googleapis.com"

# Try different calendar API names
echo "🗓️ Enabling Calendar API..."
if ! enable_api "calendar-json.googleapis.com"; then
    if ! enable_api "calendar.googleapis.com"; then
        echo "⚠️  Calendar API not enabled - you can enable it manually later"
    fi
fi

# Try Gmail API
echo "📧 Enabling Gmail API..."
if ! enable_api "gmail.googleapis.com"; then
    echo "⚠️  Gmail API not enabled - you can enable it manually later"
fi

echo "✅ Core APIs enabled"

# Create service account
echo "🔐 Creating service account..."
SA_NAME="kirlewai-backend"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
    gcloud iam service-accounts create $SA_NAME \
        --display-name="KirlewAI Backend Service Account"
    
    # Grant core permissions
    echo "Setting up basic permissions..."
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/ml.developer"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/cloudsql.client"
    
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/storage.objectViewer"
    
    echo "✅ Service account created with available permissions"
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
JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || echo "your-random-jwt-secret")
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
echo "1. Enable remaining APIs manually if needed:"
echo "   - Go to: https://console.cloud.google.com/apis/library?project=$PROJECT_ID"
echo "   - Search for and enable: Gmail API, Google Calendar API"
echo "2. Set up OAuth consent screen:"
echo "   - Go to: https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
echo "3. Create OAuth credentials:"
echo "   - Go to: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo "4. Update .env file with your OAuth credentials"
echo "5. Deploy your backend functions"
echo ""
echo "📁 Files created:"
echo "   - .env (environment configuration)"
echo "   - kirlewai-service-account.json (service account key)"
echo ""
echo "🔗 Project Console: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID"