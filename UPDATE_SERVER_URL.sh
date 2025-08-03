#!/bin/bash

# This script updates the SERVER_URL in MainActivity.kt with your actual Cloud Functions URL

echo "Please enter your Google Cloud Project ID:"
read PROJECT_ID

echo "Please enter your Google Cloud Region (default: us-central1):"
read REGION
if [ -z "$REGION" ]; then
    REGION="us-central1"
fi

# Generate the proper Cloud Functions URL
CLOUD_FUNCTION_URL="https://$REGION-$PROJECT_ID.cloudfunctions.net/processCommand"

echo "Updating SERVER_URL to: $CLOUD_FUNCTION_URL"

# Update the MainActivity.kt file
sed -i "s|private const val SERVER_URL = \"[^\"]*\"|private const val SERVER_URL = \"$CLOUD_FUNCTION_URL\"|g" android/app/src/main/java/com/kirlewai/agent/MainActivity.kt

echo "SERVER_URL updated successfully!"
echo ""
echo "Please ensure you have deployed your Cloud Function with the name 'processCommand' in your project."
echo "If you haven't deployed it yet, please do so using Google Cloud Console or gcloud CLI."
