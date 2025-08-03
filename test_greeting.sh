#!/bin/bash

echo "======================================"
echo "KirlewPHone Greeting Test Script"
echo "======================================"

# Install the app
echo "Installing app..."
adb install -r android/app/build/outputs/apk/debug/app-debug.apk

if [ $? -ne 0 ]; then
    echo "Installation failed!"
    exit 1
fi

echo "Launching app..."
adb shell am start -n com.kirlewai.agent/.MainActivity

echo ""
echo "======================================"
echo "Testing Instructions:"
echo "======================================"
echo "1. In the app, type 'hello' and press Send"
echo "2. Watch the command output area"
echo "3. It should show:"
echo "   You: hello"
echo "   Assistant: [actual AI response]"
echo ""
echo "Monitor logs with:"
echo "  adb logcat | grep KirlewPHone"
echo ""
echo "Look for these log entries:"
echo "- sendCommandToAI called with command: 'hello'"
echo "- Response Content-Type"
echo "- X-Response-Text header"
echo "======================================"