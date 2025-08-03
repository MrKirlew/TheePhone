#!/bin/bash

# Test script to diagnose and fix the 404 error

echo "🔍 Diagnosing KirlewPHone API 404 Error..."
echo ""

# Check project configuration
echo "📋 Current Google Cloud Configuration:"
gcloud config get-value project 2>/dev/null || echo "❌ No project set"
echo ""

# List deployed functions
echo "📋 Currently deployed Cloud Functions in us-central1:"
gcloud functions list --region=us-central1 2>/dev/null || echo "❌ Cannot list functions (need to authenticate)"
echo ""

# Check if the expected function exists
FUNCTION_NAME="multimodal-agent-orchestrator"
REGION="us-central1"
PROJECT_ID="twothreeatefi"

echo "🔍 Checking for function: $FUNCTION_NAME"
gcloud functions describe $FUNCTION_NAME --region=$REGION --project=$PROJECT_ID 2>/dev/null || echo "❌ Function not found"
echo ""

# Test the endpoint directly
ENDPOINT_URL="https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator"
echo "🌐 Testing endpoint directly: $ENDPOINT_URL"
curl -X POST "$ENDPOINT_URL" -H "Content-Type: application/json" -d '{"test": "ping"}' -w "\nHTTP Status: %{http_code}\n" 2>/dev/null || echo "Failed to connect"
echo ""

echo "📋 Diagnosis Summary:"
echo "-------------------"
echo "1. If you see '404 Not Found', the function is not deployed or has a different name"
echo "2. If you see '405 Method Not Allowed', the function exists but needs proper request format"
echo "3. If you see '401/403', the function exists but requires authentication"
echo ""
echo "🛠️ To fix the 404 error:"
echo "1. First, authenticate: gcloud auth login"
echo "2. Set project: gcloud config set project $PROJECT_ID"
echo "3. Deploy the function: cd backend && ./deploy_orchestrator.sh"
echo "4. Wait 2-3 minutes for deployment to complete"
echo "5. Test again with your Android app"
