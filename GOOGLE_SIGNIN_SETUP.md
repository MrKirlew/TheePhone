# Google Sign-In Setup Guide

## Current Status
✅ Web Client ID is configured: `843267258954-mc04n5od104s75to3umjl46rva3p0r0s.apps.googleusercontent.com`
✅ Cloud Function URL is set: `https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator`
✅ App builds successfully

## Google Cloud Console Configuration

### 1. Verify OAuth 2.0 Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project `twothreeatefi`
3. Navigate to **APIs & Services** → **Credentials**
4. Verify you have an OAuth 2.0 Client ID of type "Web application"

### 2. Configure OAuth Consent Screen
1. Go to **APIs & Services** → **OAuth consent screen**
2. Ensure these settings:
   - Publishing status: Testing or Production
   - Add test users (if in Testing mode)
   - Scopes included:
     - `email`
     - `profile`
     - `openid`
     - `https://www.googleapis.com/auth/calendar.readonly`
     - `https://www.googleapis.com/auth/gmail.readonly`

### 3. Android App Configuration
For the Android app to work with Google Sign-In, you need to:

1. **Add your Android app's SHA-1 fingerprint** to Google Cloud Console:
   ```bash
   # Get debug SHA-1
   cd /home/kirlewubuntu/Downloads/KirlewPHone/android
   ./gradlew signingReport
   ```
   
2. In Google Cloud Console:
   - Go to **APIs & Services** → **Credentials**
   - Create a new OAuth 2.0 Client ID of type "Android"
   - Package name: `com.kirlewai.agent`
   - SHA-1 fingerprint: (paste from above command)

### 4. Important Notes
- You're using standalone Google Sign-In (not Firebase)
- The Web Client ID is used for obtaining the server auth code
- No google-services.json is needed for this setup

## Testing Google Sign-In

1. Install the app on your device/emulator:
   ```bash
   cd /home/kirlewubuntu/Downloads/KirlewPHone/android
   ./gradlew installDebug
   ```

2. Launch the app and tap "Sign In with Google"

3. If sign-in fails, check:
   - OAuth consent screen is properly configured
   - Your Google account is added as a test user (if in Testing mode)
   - The SHA-1 fingerprint matches your debug keystore

## Troubleshooting

### Common Issues:
1. **Error 10**: Missing Android OAuth client configuration
   - Solution: Add Android OAuth client with correct SHA-1

2. **Error 12500**: Sign-in configuration issue
   - Solution: Verify OAuth consent screen settings

3. **Error 12501**: User cancelled sign-in
   - This is normal user behavior

4. **Network errors**: 
   - Ensure device has internet connection
   - Check if Google Play Services is up to date

## Next Steps
1. Get your debug SHA-1 fingerprint
2. Add Android OAuth client in Google Cloud Console
3. Test sign-in functionality
4. For production, add release SHA-1 fingerprint