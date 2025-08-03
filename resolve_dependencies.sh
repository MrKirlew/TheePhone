#!/bin/bash
# Dependency Resolution Script for KirlewPHone

echo "=== KirlewPHone Dependency Resolution ==="
echo

# Navigate to the project directory
cd /home/kirlewubuntu/Downloads/KirlewPHone/android

echo "Cleaning Gradle cache..."
./gradlew clean --refresh-dependencies

echo
echo "Updating dependencies..."
./gradlew --refresh-dependencies

echo
echo "Attempting to build the project..."
./gradlew build

echo
echo "=== Dependency Resolution Complete ==="
echo

echo "If build issues persist, try these additional steps:"
echo "1. Delete .gradle folder in the project root"
echo "2. Run: ./gradlew clean build --refresh-dependencies"
echo "3. Check that you have internet connectivity"
echo "4. Ensure Android Studio is updated to the latest version"
