#!/bin/bash

# Deployment script for ADK Mobile App

set -e

PROJECT_ID="twothreeatefi"
REGION="us-central1"

echo "Starting deployment of ADK Mobile App..."

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
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
  geocoding.googleapis.com \
  storage-api.googleapis.com \
  storage-component.googleapis.com

# Setup Firestore
echo "Setting up Firestore..."
gcloud firestore databases create --location=us-central1 --type=firestore-native || echo "Firestore already exists"

# Create secrets
echo "Creating secrets (replace with actual values)..."
echo -n "YOUR_GOOGLE_API_KEY_VALUE" | gcloud secrets create GOOGLE_API_KEY --data-file=- || echo "GOOGLE_API_KEY already exists"
echo -n "YOUR_MAPS_API_KEY_VALUE" | gcloud secrets create MAP_API_KEY --data-file=- || echo "MAP_API_KEY already exists"
echo -n "YOUR_OWM_API_KEY_VALUE" | gcloud secrets create OWM_API_KEY --data-file=- || echo "OWM_API_KEY already exists"

# Deploy backend to Cloud Run
echo "Deploying backend to Cloud Run..."
cd backend/app
gcloud builds submit --config cloudbuild.yaml --substitutions=_PROJECT_ID=$PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe adk-mobile-backend --region $REGION --format 'value(status.url)')
echo "Backend deployed at: $SERVICE_URL"

# Update Flutter client
echo "Updating Flutter client with backend URL..."
cd ../../flutter_client
sed -i "s|https://YOUR_CLOUD_RUN_URL|$SERVICE_URL|g" lib/main.dart

echo "Deployment completed successfully!"
echo "Backend URL: $SERVICE_URL"
echo "Remember to update the API keys in Secret Manager with actual values."
