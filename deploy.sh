#!/bin/bash
# Deployment script for Kirlew AI Agent

set -e

echo "🚀 Starting deployment of Kirlew AI Agent..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Variables (update these with your values)
PROJECT_ID=""
REGION="us-central1"
FUNCTION_NAME="multimodal-agent-orchestrator"
SECRET_NAME="oauth-client-secret"

# Prompt for project ID if not set
if [ -z "$PROJECT_ID" ]; then
    read -p "Enter your Google Cloud Project ID: " PROJECT_ID
fi

echo "📋 Using Project ID: $PROJECT_ID"
echo "📍 Region: $REGION"

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable iam.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable gmail.googleapis.com
gcloud services enable calendar-json.googleapis.com

echo "✅ APIs enabled successfully"

# Check if OAuth client secret exists
echo "🔐 Checking for OAuth client secret..."
if ! gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &> /dev/null; then
    echo "❌ OAuth client secret not found in Secret Manager"
    echo "Please create it first using:"
    echo "gcloud secrets create $SECRET_NAME --data-file=path/to/your/client_secret.json"
    exit 1
fi

# Grant Cloud Functions service account access to the secret
echo "🔑 Granting permissions to Cloud Functions service account..."
# Get the project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Using service account: $SERVICE_ACCOUNT"
gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

# Deploy the Cloud Function
echo "☁️ Deploying Cloud Function..."
cd backend
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=multimodal_agent_orchestrator \
    --trigger-http \
    --allow-unauthenticated=false \
    --set-env-vars SECRET_NAME=$SECRET_NAME \
    --memory=512MB \
    --timeout=60s

# Get the function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format='value(serviceConfig.uri)')
echo "✅ Cloud Function deployed successfully!"
echo "🌐 Function URL: $FUNCTION_URL"

# Set up budget alert
echo "💰 Setting up budget alert..."
read -p "Would you like to set up a $35/month budget alert? (y/n): " setup_budget
if [ "$setup_budget" = "y" ]; then
    gcloud billing budgets create \
        --billing-account=$(gcloud beta billing projects describe $PROJECT_ID --format='value(billingAccountName)') \
        --display-name="AI Agent Monthly Budget" \
        --budget-amount=35USD \
        --threshold-rule=percent=50 \
        --threshold-rule=percent=90 \
        --threshold-rule=percent=100
    echo "✅ Budget alert created"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📱 Next steps for Android app:"
echo "1. Update CLOUD_FUNCTION_URL in MainActivity.kt with: $FUNCTION_URL"
echo "2. Update WEB_CLIENT_ID in MainActivity.kt with your Web Application Client ID"
echo "3. Build and install the Android app"
echo ""
echo "⚠️ Important reminders:"
echo "- Make sure you've created both OAuth Client IDs (Android and Web Application)"
echo "- The Web Application client_secret.json must be uploaded to Secret Manager"
echo "- Grant necessary permissions to users who will invoke the function"