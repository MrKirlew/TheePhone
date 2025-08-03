#!/bin/bash

echo "Building KirlewPHone Redesigned App..."

# Clean previous builds
echo "Cleaning previous builds..."
./gradlew clean

# Build the app
echo "Building the app..."
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "BUILD SUCCESSFUL!"
    echo "=========================================="
    echo "Your redesigned KirlewPHone app has been built successfully."
    echo ""
    echo "APK location: android/app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo "To install on an Android device:"
    echo "1. Connect your Android device via USB"
    echo "2. Enable USB debugging in Developer Options"
    echo "3. Run: adb install android/app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo "IMPORTANT SETUP STEPS:"
    echo "1. Update the SERVER_URL in MainActivity.kt with your actual Cloud Functions URL"
    echo "2. Add your Google Web Client ID to strings.xml"
    echo "3. Deploy your Cloud Function backend"
    echo ""
    echo "Your app now includes:"
    echo "- Unified command input (text, voice, advanced)"
    echo "- Google Sign In/Sign Out"
    echo "- Voice recording capability"
    echo "- Camera for image/document processing"
    echo "- Fixed network timeout errors"
    echo "- All API integrations in backend (not displayed in UI)"
    echo ""
    echo "The app is now THE GREATEST PERSONAL ASSISTANT IN THE WORLD!"
else
    echo "=========================================="
    echo "BUILD FAILED"
    echo "=========================================="
    echo "Please check the error messages above."
    echo "Common issues and solutions:"
    echo "1. Check your internet connection"
    echo "2. Verify Android SDK is properly installed"
    echo "3. Ensure all required dependencies are available"
    echo "4. Check that you have enough disk space"
fi
