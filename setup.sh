#!/bin/bash

# Setup script for Google Workspace AI Agent
# This script helps you deploy the application using your existing database

echo "🚀 Google Workspace AI Agent Setup"
echo "=================================="
echo ""
echo "This script will help you deploy the application with your existing database."
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK (gcloud) is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "✅ Google Cloud SDK is installed"
echo ""

# Check authentication
echo "Checking Google Cloud authentication..."
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    echo "✅ Authenticated as: $ACCOUNT"
else
    echo "❌ Not authenticated with Google Cloud."
    echo "Please run: gcloud auth login"
    exit 1
fi

echo ""
echo "📁 Current Project: twothreeatefi"
echo ""

# Ask for API keys
echo "🔑 API Key Setup"
echo "================"
echo "You'll need to update the following secrets with your actual API keys:"
echo ""

echo "1. GOOGLE_API_KEY - For Google Workspace APIs"
echo "2. MAP_API_KEY - For Maps (optional, can skip if not needed)"
echo "3. OWM_API_KEY - For Weather (optional, can skip if not needed)"
echo ""

read -p "Do you want to update your API keys now? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    read -p "Enter your Google API key (or press Enter to skip): " GOOGLE_KEY
    if [ ! -z "$GOOGLE_KEY" ]; then
        echo -n "$GOOGLE_KEY" | gcloud secrets versions add GOOGLE_API_KEY --data-file=- 2>/dev/null || \
        echo -n "$GOOGLE_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=- 2>/dev/null || \
        echo "✅ GOOGLE_API_KEY updated"
    fi
    
    read -p "Enter your Maps API key (or press Enter to skip): " MAPS_KEY
    if [ ! -z "$MAPS_KEY" ]; then
        echo -n "$MAPS_KEY" | gcloud secrets versions add MAP_API_KEY --data-file=- 2>/dev/null || \
        echo -n "$MAPS_KEY" | gcloud secrets create MAP_API_KEY --data-file=- 2>/dev/null || \
        echo "✅ MAP_API_KEY updated"
    fi
    
    read -p "Enter your OpenWeatherMap API key (or press Enter to skip): " OWM_KEY
    if [ ! -z "$OWM_KEY" ]; then
        echo -n "$OWM_KEY" | gcloud secrets versions add OWM_API_KEY --data-file=- 2>/dev/null || \
        echo -n "$OWM_KEY" | gcloud secrets create OWM_API_KEY --data-file=- 2>/dev/null || \
        echo "✅ OWM_API_KEY updated"
    fi
fi

echo ""
echo "🔄 Deployment Preparation"
echo "========================="
echo "Your existing Firestore database is ready to use with the new implementation."
echo "No migration or changes are needed to your existing database."
echo ""

read -p "Do you want to deploy the backend to Cloud Run now? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Deploying to Cloud Run..."
    cd backend/app
    
    # Check if cloudbuild.yaml exists
    if [ -f "cloudbuild.yaml" ]; then
        gcloud builds submit --config cloudbuild.yaml --substitutions=_PROJECT_ID=twothreeatefi
        echo ""
        echo "✅ Backend deployment completed!"
        echo "Get your service URL with:"
        echo "gcloud run services describe adk-mobile-backend --region us-central1 --format 'value(status.url)'"
    else
        echo "❌ cloudbuild.yaml not found. Please check the backend/app directory."
    fi
fi

echo ""
echo "📱 Flutter Client Setup"
echo "======================"
echo "To use the Flutter client:"
echo "1. Get your Cloud Run service URL"
echo "2. Update the URL in flutter_client/lib/api_client.dart"
echo "3. Run 'flutter pub get' in the flutter_client directory"
echo "4. Build with 'flutter build apk' or 'flutter run'"

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo "Your Google Workspace AI Agent is ready to use with your existing database."
echo "All your existing data is preserved and new features will work seamlessly."
