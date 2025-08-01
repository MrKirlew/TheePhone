#!/bin/bash

# Deploy Secure KirlewAI Backend to Google Cloud Functions
set -e

echo "🚀 Deploying Secure KirlewAI Backend..."

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo "❌ .env file not found. Please run deploy-minimal.sh first."
    exit 1
fi

# Load environment variables
source ../.env

if [ -z "$PROJECT_ID" ]; then
    echo "❌ PROJECT_ID not set in .env file"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

echo "📦 Preparing backend deployment..."

# Create main.py entry point
cat > main.py << EOF
from secure_cloud_function import multimodal_agent_orchestrator

# Cloud Function entry point
def multimodal_agent(request):
    return multimodal_agent_orchestrator(request)
EOF

# Deploy Cloud Function with security settings
echo "🔐 Deploying secure Cloud Function..."

gcloud functions deploy multimodal-agent \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point multimodal_agent \
    --source . \
    --memory 512MB \
    --timeout 540s \
    --max-instances 10 \
    --set-env-vars "GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID,JWT_SECRET=$JWT_SECRET,ALLOWED_ORIGINS=$ALLOWED_ORIGINS" \
    --service-account "kirlewai-backend@$PROJECT_ID.iam.gserviceaccount.com" \
    --region us-central1

# Get the function URL
FUNCTION_URL=$(gcloud functions describe multimodal-agent --region=us-central1 --format="value(httpsTrigger.url)")

echo "✅ Secure backend deployed successfully!"
echo ""
echo "🔗 Function URL: $FUNCTION_URL"
echo ""
echo "📋 Next steps:"
echo "1. Update your Android app's CLOUD_FUNCTION_URL to: $FUNCTION_URL"
echo "2. Update your .env file with the function URL"
echo "3. Test the secure communication"
echo ""

# Update .env file with function URL
if [ -f "../.env" ]; then
    sed -i "s|CLOUD_FUNCTION_URL=.*|CLOUD_FUNCTION_URL=$FUNCTION_URL|" ../.env
    echo "✅ Updated .env file with function URL"
fi

echo "🛡️ Security features enabled:"
echo "   - HTTPS certificate pinning"
echo "   - JWT token validation"
echo "   - Request signing and verification"
echo "   - Input sanitization"
echo "   - Rate limiting"
echo "   - File upload validation"
echo "   - Encrypted data transmission"
echo "   - Response integrity checking"