#!/bin/bash

# Deployment script for ADK Mobile Service

set -e

PROJECT_ID="twothreeatefi"
REGION="us-central1"
SERVICE_NAME="adk-mobile-service"

echo "Starting deployment of ADK Mobile Service..."

# Set the project
echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs (skip those that might not be available)
echo "Enabling required APIs..."
for api in \
  run.googleapis.com \
  secretmanager.googleapis.com \
  firestore.googleapis.com \
  cloudapis.googleapis.com \
  cloudresourcemanager.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudbuild.googleapis.com \
  vision.googleapis.com \
  speech.googleapis.com \
  storage-api.googleapis.com \
  storage-component.googleapis.com \
  appengine.googleapis.com \
  containerregistry.googleapis.com; do
  echo "Enabling $api..."
  gcloud services enable $api 2>/dev/null || echo "  Warning: Could not enable $api (may require additional permissions or may not be available)"
done

# Setup Firestore if not exists
echo "Setting up Firestore..."
gcloud firestore databases create --location=$REGION --type=firestore-native 2>/dev/null || echo "Firestore database already exists"

# Create secrets if they don't exist
echo "Checking and creating secrets..."
gcloud secrets describe GOOGLE_API_KEY 2>/dev/null || \
  echo -n "YOUR_GOOGLE_API_KEY_VALUE" | gcloud secrets create GOOGLE_API_KEY --data-file=-

gcloud secrets describe MAP_API_KEY 2>/dev/null || \
  echo -n "YOUR_MAPS_API_KEY_VALUE" | gcloud secrets create MAP_API_KEY --data-file=-

gcloud secrets describe OWM_API_KEY 2>/dev/null || \
  echo -n "YOUR_OWM_API_KEY_VALUE" | gcloud secrets create OWM_API_KEY --data-file=-

# Grant Cloud Run service account access to secrets
echo "Granting service account access to secrets..."
# Get the project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
# Use the default compute service account for Cloud Run
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Using service account: ${SERVICE_ACCOUNT}"

gcloud secrets add-iam-policy-binding GOOGLE_API_KEY \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" --quiet 2>/dev/null || echo "  Note: Could not grant access to GOOGLE_API_KEY"

gcloud secrets add-iam-policy-binding MAP_API_KEY \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" --quiet 2>/dev/null || echo "  Note: Could not grant access to MAP_API_KEY"

gcloud secrets add-iam-policy-binding OWM_API_KEY \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" --quiet 2>/dev/null || echo "  Note: Could not grant access to OWM_API_KEY"

# Deploy backend to Cloud Run using Cloud Build
echo "Deploying $SERVICE_NAME to Cloud Run..."
cd backend/app
gcloud builds submit --config cloudbuild.yaml --substitutions=_PROJECT_ID=$PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
echo "Service Name: $SERVICE_NAME"
echo "Service URL: $SERVICE_URL"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""
echo "IMPORTANT: Remember to update the API keys in Secret Manager with actual values:"
echo "  - GOOGLE_API_KEY"
echo "  - MAP_API_KEY"
echo "  - OWM_API_KEY"
echo ""
echo "To update a secret, use:"
echo "  echo -n 'YOUR_ACTUAL_KEY' | gcloud secrets versions add SECRET_NAME --data-file=-"
echo ""
echo "To test the service:"
echo "  curl $SERVICE_URL/health"