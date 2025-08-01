# KirlewAI Multimodal Agent with Gemini Integration

This Cloud Function implements a powerful multimodal AI agent using Google's Gemini API for advanced language understanding and generation.

## Features

### 🤖 Gemini-Powered Intelligence
- **Multimodal Understanding**: Process text, audio, and images simultaneously
- **Contextual Conversations**: Maintains conversation history for coherent interactions
- **Advanced Language Models**: Uses Gemini Pro and Gemini Pro Vision models
- **Entity Extraction**: Automatically identifies people, places, dates, and more
- **Sentiment Analysis**: Understands emotional tone and context

### 🎙️ Speech Processing
- **Google Cloud Speech-to-Text**: Transcribes audio with high accuracy
- **Multiple Audio Formats**: Supports AMR, WAV, MP3
- **Enhanced Models**: Uses latest_long model for better accuracy
- **Automatic Punctuation**: Adds punctuation for natural text

### 🔊 Audio Generation
- **Neural Text-to-Speech**: High-quality voice synthesis
- **Multiple Voices**: Various voice options available
- **Natural Prosody**: Sounds natural and conversational

### 🔒 Security Features
- **OAuth2 Authentication**: Secure user authentication
- **Input Sanitization**: Prevents injection attacks
- **Safety Checks**: Content moderation using Gemini
- **Audit Logging**: Comprehensive activity logging

## API Endpoints

### `/multimodal-agent` (POST)
Main endpoint for multimodal processing.

**Request:**
- `voice_command` or `text_command`: Text input
- `audio_file`: Audio file for transcription (optional)
- `image_file`: Image for analysis (optional)
- `session_id`: Session identifier
- `auth_code`: Authentication code

**Response:**
- Audio file (MP3) with AI response

### `/transcribe` (POST)
Transcribe audio to text.

**Request:**
- `audio_file`: Audio file to transcribe

**Response:**
```json
{
  "success": true,
  "transcription": "Transcribed text here"
}
```

### `/process-text` (POST)
Process text with Gemini.

**Request:**
```json
{
  "text": "Your question or command",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "success": true,
  "response": "AI response",
  "model_used": "gemini-pro",
  "entities": {...},
  "sentiment": {...}
}
```

## Deployment

1. **Set up Google Cloud Project**
   ```bash
   gcloud config set project twothreeatefi
   ```

2. **Enable Required APIs**
   ```bash
   gcloud services enable cloudfunctions.googleapis.com
   gcloud services enable speech.googleapis.com
   gcloud services enable texttospeech.googleapis.com
   gcloud services enable generativelanguage.googleapis.com
   ```

3. **Set Environment Variables**
   ```bash
   # Get your Gemini API key from Google AI Studio
   export GEMINI_API_KEY="your-gemini-api-key"
   ```

4. **Deploy the Function**
   ```bash
   gcloud functions deploy multimodal-agent-orchestrator \
     --runtime python312 \
     --trigger-http \
     --allow-unauthenticated \
     --memory 2GB \
     --timeout 540s \
     --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
     --region us-central1
   ```

## Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export GEMINI_API_KEY="your-api-key"
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
   ```

3. **Run Locally**
   ```bash
   python secure_cloud_function.py
   ```

## Gemini Integration Details

### Models Used

1. **Gemini Pro**: For text-only interactions
   - Advanced reasoning and understanding
   - Context-aware responses
   - Multi-turn conversations

2. **Gemini Pro Vision**: For image + text interactions
   - Image understanding and analysis
   - Visual question answering
   - Scene description

### Key Features

- **Conversation Memory**: Maintains context across interactions
- **Safety Filtering**: Built-in content moderation
- **Entity Recognition**: Extracts key information
- **Sentiment Analysis**: Understands emotional context
- **Summarization**: Can summarize long conversations

### Example Use Cases

1. **Visual Assistant**
   - "What's in this image?"
   - "How many people do you see?"
   - "What should I cook with these ingredients?" (with photo)

2. **Conversational AI**
   - Natural back-and-forth dialogue
   - Remembers previous context
   - Provides detailed explanations

3. **Task Automation**
   - Extract information from documents
   - Analyze and summarize content
   - Answer questions about data

## Cost Optimization

- Uses efficient model selection (Pro vs Pro Vision)
- Caches frequently used responses
- Implements token limits for cost control
- Monitors usage through Cloud Logging

## Monitoring

View logs:
```bash
gcloud functions logs read multimodal-agent-orchestrator --limit 50
```

## Security Best Practices

1. **API Key Management**: Store in Secret Manager
2. **Input Validation**: All inputs are sanitized
3. **Rate Limiting**: Implement at API Gateway level
4. **Authentication**: Requires valid OAuth tokens
5. **Audit Logging**: All requests are logged

## Troubleshooting

### Common Issues

1. **Gemini API Key**: Ensure it's set in environment
2. **Permissions**: Service account needs proper roles
3. **Quotas**: Check API quotas in Cloud Console
4. **Timeouts**: Increase function timeout for complex requests

### Debug Mode

Set `LOG_LEVEL=DEBUG` for verbose logging:
```bash
gcloud functions deploy ... --set-env-vars LOG_LEVEL=DEBUG
```