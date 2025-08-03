#!/bin/bash

# Deploy Multimodal Agent Orchestrator to Google Cloud Functions
set -e

echo "🚀 Deploying Multimodal Agent Orchestrator..."

# Set variables
PROJECT_ID="twothreeatefi"
FUNCTION_NAME="multimodal-agent-orchestrator"
REGION="us-central1"

# Set project
gcloud config set project $PROJECT_ID

echo "📦 Installing dependencies..."

# Create requirements.txt if it doesn't exist
cat > requirements.txt << EOF
functions-framework==3.*
google-cloud-speech==2.*
google-cloud-texttospeech==2.*
google-cloud-secret-manager==2.*
google-cloud-vision==3.*
google-cloud-aiplatform==1.*
google-auth==2.*
google-auth-oauthlib==1.*
google-api-python-client==2.*
vertexai
Werkzeug==2.*
EOF

echo "🔐 Deploying Cloud Function..."

# Deploy the function using main.py as the source
gcloud functions deploy $FUNCTION_NAME \
    --runtime python312 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point multimodal_agent_orchestrator \
    --source . \
    --memory 2048MB \
    --timeout 540s \
    --max-instances 100 \
    --min-instances 1 \
    --region $REGION \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"

# Get the function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format="value(httpsTrigger.url)")

echo "✅ Multimodal Agent Orchestrator deployed successfully!"
echo ""
echo "🔗 Function URL: $FUNCTION_URL"
echo ""
echo "📋 The Android app should already be configured to use this URL:"
echo "   https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator"
echo ""
echo "🛡️ Features enabled:"
echo "   - Speech-to-Text transcription"
echo "   - Gemini 1.5 Pro multimodal AI"
echo "   - Text-to-Speech synthesis"
echo "   - Google Workspace integration"
echo "   - Image analysis with Vision API"
echo "   - OAuth 2.0 authentication"
