#!/bin/bash

# Simplified deployment script for ADK Mobile App

set -e

PROJECT_ID="twothreeatefi"
REGION="us-central1"

echo "Starting simplified deployment of ADK Mobile App..."

# Try to enable core APIs (ignore errors for problematic ones)
echo "Enabling core APIs..."
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  firestore.googleapis.com \
  cloudapis.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudbuild.googleapis.com || echo "Some APIs could not be enabled, continuing..."

# Setup Firestore
echo "Setting up Firestore..."
gcloud firestore databases create --location=us-central1 --type=firestore-native || echo "Firestore setup completed or already exists"

# Create secrets (you'll need to update these with actual values)
echo "Creating placeholder secrets..."
echo -n "YOUR_GOOGLE_API_KEY_VALUE" | gcloud secrets create GOOGLE_API_KEY --data-file=- 2>/dev/null || echo "GOOGLE_API_KEY secret already exists or couldn't be created"
echo -n "YOUR_MAPS_API_KEY_VALUE" | gcloud secrets create MAP_API_KEY --data-file=- 2>/dev/null || echo "MAP_API_KEY secret already exists or couldn't be created"
echo -n "YOUR_OWM_API_KEY_VALUE" | gcloud secrets create OWM_API_KEY --data-file=- 2>/dev/null || echo "OWM_API_KEY secret already exists or couldn't be created"

echo "Deployment preparation completed!"
echo "Please remember to:"
echo "1. Update the API keys in Secret Manager with actual values"
echo "2. Manually enable any additional APIs you need through the Google Cloud Console"
echo "3. Configure proper IAM permissions for your service account"
