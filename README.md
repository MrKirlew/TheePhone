# Kirlew AI Agent - Secure Mobile App

A powerful, budget-conscious multimodal AI agent built on Google Cloud that integrates with Google Workspace services. This app allows users to interact with an AI assistant using voice commands and images, with the AI having access to their calendar and email data.

## Architecture Overview

- **Backend**: Google Cloud Functions (Python) orchestrating Vertex AI services
- **Frontend**: Android app with voice recording and camera capabilities
- **AI Model**: Gemini 1.5 Pro for multimodal understanding
- **Services**: Speech-to-Text, Text-to-Speech, Gmail API, Calendar API
- **Budget**: Designed to operate within $35/month

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Android Studio** for mobile app development
3. **gcloud CLI** installed and configured
4. **Python 3.11+** for backend development

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd KirlewPHone
```

### 2. Google Cloud Setup

#### Create OAuth 2.0 Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to "APIs & Services" → "Credentials"
3. Create TWO OAuth 2.0 Client IDs:
   - **Android Client ID**: For the mobile app
   - **Web Application Client ID**: For the backend (download the JSON)

#### Upload Client Secret
```bash
gcloud secrets create oauth-client-secret --data-file=path/to/client_secret.json
```

### 3. Deploy Backend

Run the deployment script:
```bash
./deploy.sh
```

This script will:
- Enable required Google Cloud APIs
- Deploy the Cloud Function
- Set up budget alerts
- Provide the function URL for your Android app

### 4. Configure Android App

1. Open `android/app/src/main/java/com/kirlewai/agent/MainActivity.kt`
2. Update these constants:
   ```kotlin
   private const val CLOUD_FUNCTION_URL = "YOUR_FUNCTION_URL"
   private const val WEB_CLIENT_ID = "YOUR_WEB_CLIENT_ID.apps.googleusercontent.com"
   ```

3. Build and run the app in Android Studio

## Project Structure

```
KirlewPHone/
├── backend/
│   ├── main.py              # Cloud Function orchestrator
│   └── requirements.txt     # Python dependencies
├── android/
│   └── app/                 # Android application
├── .github/workflows/       # CI/CD pipelines
├── deploy.sh               # Deployment script
└── README.md              # This file
```

## Features

- **Voice Commands**: Record and transcribe voice queries
- **Image Capture**: Take photos for visual context
- **Google Workspace Integration**: Access calendar events and emails
- **Multimodal AI**: Gemini 1.5 Pro processes text, voice, and images
- **Natural Speech**: Text-to-Speech for AI responses
- **Secure Authentication**: OAuth 2.0 server-side flow

## Cost Optimization

The app is designed to stay within $35/month by:
- Using Google Cloud free tiers
- Offering Standard vs WaveNet voice options
- Efficient prompt engineering
- Serverless architecture (pay only for usage)

### Monthly Cost Breakdown (Moderate Use - 30 queries/day)
- Gemini 1.5 Pro: ~$4.17
- Speech-to-Text: ~$2.64
- Text-to-Speech: ~$5.60 (WaveNet) or ~$0.56 (Standard)
- Cloud Functions: ~$0.00 (within free tier)
- **Total**: ~$12.41/month (WaveNet) or ~$7.37/month (Standard)

## Security Considerations

- OAuth 2.0 server-side flow prevents credential exposure
- Cloud Function requires authentication
- Client secrets stored in Google Secret Manager
- Minimal permissions requested (read-only access)

## Development

### Backend Testing
```bash
cd backend
pip install -r requirements.txt
python -m pytest
```

### Android Development
1. Open the `android` folder in Android Studio
2. Sync Gradle files
3. Run on emulator or physical device

## CI/CD

GitHub Actions workflows are configured for:
- **Backend CI**: Linting and testing on every push
- **Backend CD**: Automatic deployment to Google Cloud
- **Android CI**: Build and test Android app

## Troubleshooting

### "Invalid grant" error
- Ensure you're using the Web Application Client ID in the Android app
- Verify the client secret is correctly uploaded to Secret Manager

### Audio not playing
- Check Android permissions for audio playback
- Verify the Cloud Function returns audio/mpeg content type

### High costs
- Switch from WaveNet to Standard voices
- Implement response length limits
- Monitor usage in Google Cloud Console

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is provided as-is for educational and development purposes.

## Support

For issues and questions:
- Check the [deployment plan](Secure%20Mobile%20App%20Deployment%20Plan_.txt) for detailed instructions
- Review Google Cloud logs for backend errors
- Use Android Studio logcat for mobile app debugging