# Kirlew AI Agent - Complete Setup Guide

This guide walks you through setting up the Kirlew AI Agent from scratch.

## Step 1: Google Cloud Project Setup

### 1.1 Create a New Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Select a project" → "NEW PROJECT"
3. Name: "kirlew-ai-agent" (or your preference)
4. Note the Project ID (you'll need this later)
5. Click "CREATE"

### 1.2 Enable Billing
1. In the left menu, go to "Billing"
2. Link a billing account or create a new one
3. Enable billing for your project

### 1.3 Enable APIs
Run these commands in Cloud Shell or your local terminal:
```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable iam.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable gmail.googleapis.com
gcloud services enable calendar-json.googleapis.com
```

## Step 2: OAuth 2.0 Configuration

### 2.1 Configure OAuth Consent Screen
1. Go to "APIs & Services" → "OAuth consent screen"
2. Choose "External" (or "Internal" if using Google Workspace)
3. Fill in:
   - App name: "Kirlew AI Agent"
   - User support email: Your email
   - Developer contact: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/calendar.readonly`
5. Add test users (your email)
6. Save and continue

### 2.2 Create OAuth Client IDs

#### Android Client ID:
1. Go to "APIs & Services" → "Credentials"
2. Click "CREATE CREDENTIALS" → "OAuth client ID"
3. Application type: "Android"
4. Name: "Kirlew AI Agent Android"
5. Package name: `com.kirlewai.agent`
6. SHA-1 fingerprint: 
   ```bash
   # Get from Android Studio or run:
   keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android
   ```
7. Click "CREATE"

#### Web Application Client ID:
1. Click "CREATE CREDENTIALS" → "OAuth client ID" again
2. Application type: "Web application"
3. Name: "Kirlew AI Agent Backend"
4. Authorized redirect URIs: Add `https://localhost` (for testing)
5. Click "CREATE"
6. **DOWNLOAD THE JSON** (click the download button)
7. Save as `client_secret.json`

## Step 3: Upload Client Secret

```bash
# Upload the client secret to Secret Manager
gcloud secrets create oauth-client-secret --data-file=client_secret.json
```

## Step 4: Deploy Backend

### 4.1 Clone the Repository
```bash
git clone <repository-url>
cd KirlewPHone
```

### 4.2 Run Deployment Script
```bash
./deploy.sh
```

When prompted:
- Enter your Project ID
- Choose "y" to set up budget alerts

### 4.3 Note the Function URL
The script will output something like:
```
Function URL: https://us-central1-YOUR-PROJECT.cloudfunctions.net/multimodal-agent-orchestrator
```

Save this URL!

## Step 5: Configure Android App

### 5.1 Update Constants
Edit `android/app/src/main/java/com/kirlewai/agent/MainActivity.kt`:

```kotlin
companion object {
    // ... other constants ...
    
    // Replace with your function URL from Step 4.3
    private const val CLOUD_FUNCTION_URL = "https://us-central1-YOUR-PROJECT.cloudfunctions.net/multimodal-agent-orchestrator"
    
    // Replace with your Web Application Client ID from Step 2.2
    private const val WEB_CLIENT_ID = "YOUR-WEB-CLIENT-ID.apps.googleusercontent.com"
}
```

### 5.2 Build and Install
1. Open Android Studio
2. Open the `android` folder as a project
3. Wait for Gradle sync
4. Connect your Android device or start an emulator
5. Click "Run" (green play button)

## Step 6: Grant Permissions

When the app launches:
1. Grant microphone permission
2. Grant camera permission
3. Sign in with your Google account
4. Allow the requested permissions

## Step 7: Test the App

1. **Sign In**: Tap "Sign In with Google"
2. **Record**: Hold "Start Recording" and speak your query
3. **Photo** (optional): Tap "Capture Photo"
4. **Send**: Tap "Send to AI Agent"
5. **Listen**: The AI will respond with speech

## Step 8: Set Up Budget Monitoring

### 8.1 Create Budget Alert (if not done in deploy.sh)
1. Go to "Billing" → "Budgets & alerts"
2. Click "CREATE BUDGET"
3. Name: "AI Agent Monthly Budget"
4. Amount: $35
5. Set alerts at: 50%, 90%, 100%
6. Add your email for notifications

### 8.2 Monitor Usage
- Check daily: [Google Cloud Console](https://console.cloud.google.com) → "Billing"
- View API usage: "APIs & Services" → "Dashboard"

## Troubleshooting

### "Sign-in failed"
- Verify the Web Client ID is correct in MainActivity.kt
- Check that the package name matches in the Android OAuth client
- Ensure test users are added in OAuth consent screen

### "Missing required form parts"
- Make sure you recorded audio before sending
- Check that sign-in was successful

### "Internal Server Error"
- Check Cloud Function logs:
  ```bash
  gcloud functions logs read multimodal-agent-orchestrator --limit 50
  ```
- Verify the client secret is uploaded correctly
- Check API enablement

### High Costs
- Switch to Standard voice in backend/main.py:
  ```python
  response_audio_bytes = synthesize_speech(gemini_response_text, voice_choice="Standard")
  ```

## Next Steps

1. **Customize the AI prompt** in `backend/main.py` → `generate_gemini_response()`
2. **Add more Google services** by requesting additional OAuth scopes
3. **Implement conversation history** using Firestore
4. **Add user preferences** for voice selection
5. **Create a production release** with proper signing keys

## Support Resources

- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Android Developer Guide](https://developer.android.com/guide)
- [OAuth 2.0 Best Practices](https://www.oauth.com/oauth2-servers/access-tokens/)

Remember to regularly check your billing to ensure you stay within budget!