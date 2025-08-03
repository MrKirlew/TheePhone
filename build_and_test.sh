#!/bin/bash

# Build and test script for KirlewPHone

echo "===================================="
echo "KirlewPHone Build and Test Script"
echo "===================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "android/app/build.gradle" ]; then
    echo -e "${RED}Error: Not in KirlewPHone root directory${NC}"
    exit 1
fi

echo -e "${GREEN}Building Android app...${NC}"
cd android

# Clean previous builds
./gradlew clean

# Build debug APK
./gradlew assembleDebug

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful!${NC}"
    echo "APK location: android/app/build/outputs/apk/debug/app-debug.apk"
    
    # Check if device is connected
    if adb devices | grep -q "device$"; then
        echo -e "${GREEN}Installing on connected device...${NC}"
        adb install -r app/build/outputs/apk/debug/app-debug.apk
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Installation successful!${NC}"
            echo -e "${GREEN}Launching app...${NC}"
            adb shell am start -n com.kirlewai.agent/.MainActivity
        fi
    else
        echo "No device connected. Connect a device and run:"
        echo "  adb install -r android/app/build/outputs/apk/debug/app-debug.apk"
    fi
else
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi

echo ""
echo "===================================="
echo "Testing Instructions:"
echo "===================================="
echo "1. Make sure you're signed in with Google"
echo "2. Test voice commands:"
echo "   - 'What's on my calendar today?'"
echo "   - 'Do I have any meetings today?'"
echo "   - 'What's my schedule for today?'"
echo "3. Check the dialogue area shows:"
echo "   - Your spoken command"
echo "   - The AI's actual response (not '[Speaking...]')"
echo "   - Full conversation history"
echo "4. Verify continuous listening works"
echo "===================================="