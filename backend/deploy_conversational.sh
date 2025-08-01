#!/bin/bash

# Deploy conversational AI backend to Google Cloud Functions

echo "🚀 Deploying Enhanced Conversational AI Backend..."

# Set variables
PROJECT_ID="twothreeatefi"
FUNCTION_NAME="conversational-agent"
REGION="us-central1"
ENTRY_POINT="conversational_agent"
RUNTIME="python310"
MEMORY="2GB"
TIMEOUT="540s"

# Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create requirements.txt if it doesn't exist
if [ ! -f "requirements.txt" ]; then
    echo "📦 Creating requirements.txt..."
    cat > requirements.txt << EOF
functions-framework==3.*
google-cloud-speech==2.*
google-cloud-texttospeech==2.*
google-cloud-secret-manager==2.*
google-cloud-firestore==2.*
google-cloud-aiplatform==1.*
google-auth==2.*
google-auth-oauthlib==1.*
google-api-python-client==2.*
Flask==2.*
Werkzeug==2.*
EOF
fi

# Deploy the function
echo "☁️ Deploying function to Google Cloud..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=$RUNTIME \
    --region=$REGION \
    --source=. \
    --entry-point=$ENTRY_POINT \
    --trigger-http \
    --allow-unauthenticated \
    --memory=$MEMORY \
    --timeout=$TIMEOUT \
    --set-env-vars="PROJECT_ID=$PROJECT_ID" \
    --project=$PROJECT_ID

# Get the function URL
echo "🔗 Getting function URL..."
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(httpsTrigger.url)" --project=$PROJECT_ID)

echo "✅ Deployment complete!"
echo "📍 Function URL: $FUNCTION_URL"
echo ""
echo "🔄 To update your Android app:"
echo "1. Replace CLOUD_FUNCTION_URL in MainActivity.kt with: $FUNCTION_URL"
echo "2. Rebuild and redeploy your Android app"
echo ""
echo "📝 Features added:"
echo "- Conversational AI with memory and personality"
echo "- User session persistence with Firestore"
echo "- Advanced reasoning and intent detection"
echo "- Natural, context-aware responses"
echo "- Emotional intelligence and rapport building"
echo "- Topic tracking and conversation history"