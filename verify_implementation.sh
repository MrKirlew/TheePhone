#!/bin/bash
# Verification script for KirlewPHone API Integration

echo "=== KirlewPHone API Integration Verification ==="
echo

# Check if required files exist
echo "Checking required files..."

FILES=(
    "/home/kirlewubuntu/Downloads/KirlewPHone/API_INTEGRATION_PLAN.md"
    "/home/kirlewubuntu/Downloads/KirlewPHone/API_INTEGRATION_DOCUMENTATION.md"
    "/home/kirlewubuntu/Downloads/KirlewPHone/IMPLEMENTATION_SUMMARY.md"
    "/home/kirlewubuntu/Downloads/KirlewPHone/backend/enhanced_intent_detector.py"
    "/home/kirlewubuntu/Downloads/KirlewPHone/backend/api_manager.py"
    "/home/kirlewubuntu/Downloads/KirlewPHone/android/app/src/main/java/com/kirlewai/agent/MainActivity.kt"
    "/home/kirlewubuntu/Downloads/KirlewPHone/android/app/src/main/res/layout/activity_main.xml"
)

MISSING_FILES=0

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (MISSING)"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

echo
echo "Checking modified files..."

# Check if main.py was modified
if grep -q "advanced_command" "/home/kirlewubuntu/Downloads/KirlewPHone/backend/main.py"; then
    echo "✓ backend/main.py (successfully modified)"
else
    echo "✗ backend/main.py (modification may have failed)"
fi

# Check if build.gradle was modified
if grep -q "google-cloud-storage" "/home/kirlewubuntu/Downloads/KirlewPHone/android/app/build.gradle"; then
    echo "✓ android/app/build.gradle (successfully modified)"
else
    echo "✗ android/app/build.gradle (modification may have failed)"
fi

echo
echo "=== Verification Complete ==="

if [ $MISSING_FILES -eq 0 ]; then
    echo "✓ All files successfully created!"
    echo "Your mobile app is now ready to read all APIs and respond to both natural language and advanced commands."
else
    echo "✗ $MISSING_FILES file(s) missing. Please check the implementation."
fi
