# main_powerful_ai.py - Production-Grade Gemini 1.5 Pro Multimodal AI Agent
import functions_framework
from werkzeug.utils import secure_filename
import os
import tempfile
import json
import logging
from flask import jsonify
import base64

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Google Cloud libraries
try:
    from google.cloud import speech
    from google.cloud import texttospeech
    from google.cloud import secretmanager
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, SafetySetting, GenerationConfig
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    import google.auth
    from datetime import datetime, timedelta
    import jwt
    import requests
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Required libraries not available: {e}")
    SERVICES_AVAILABLE = False

# Initialize Vertex AI
if SERVICES_AVAILABLE:
    try:
        vertexai.init(project="twothreeatefi", location="us-central1")
        logger.info("Vertex AI initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}")

# Google Workspace integration configuration
WORKSPACE_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

def get_web_client_secrets():
    """Fetches the OAuth client secret from Google Secret Manager"""
    try:
        _, project_id = google.auth.default()
        client = secretmanager.SecretManagerServiceClient()
        
        # Use the secret name that matches what's stored in Secret Manager
        name = f"projects/{project_id}/secrets/oauth-web-client-secret/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return json.loads(response.payload.data.decode("UTF-8"))
    except Exception as e:
        logger.error(f"Failed to get web client secrets: {e}")
        # In a production environment, ensure the secret is correctly configured in Secret Manager.
        # Fallback configurations should be avoided or handled with extreme care for security.
        raise Exception("Failed to retrieve web client secrets from Secret Manager. Ensure the secret 'oauth-web-client-secret' is configured correctly.")

def validate_id_token(id_token):
    """Validates the Google ID token."""
    try:
        # Specify the CLIENT_ID of the app that accesses the backend:
        # This should be your Android app's client ID
        # For now, using a placeholder, replace with your actual Android client ID
        CLIENT_ID = "YOUR_ANDROID_CLIENT_ID" 

        # Verify the ID token
        idinfo = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}").json()

        if idinfo.get("aud") != CLIENT_ID:
            raise ValueError("Audience mismatch")
        if idinfo.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Wrong issuer")

        # Token is valid, return the user ID
        return idinfo.get("sub")
    except Exception as e:
        logger.error(f"ID token validation failed: {e}")
        return None

def get_workspace_clients(auth_code):
    """Exchange authorization code for credentials and return API clients"""
    try:
        client_config = get_web_client_secrets()
        flow = Flow.from_client_config(client_config, scopes=WORKSPACE_SCOPES)
        flow.redirect_uri = 'postmessage'
        
        # Exchange the auth code for credentials
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        # Build API clients
        gmail_service = build('gmail', 'v1', credentials=credentials)
        calendar_service = build('calendar', 'v3', credentials=credentials)
        drive_service = build('drive', 'v3', credentials=credentials)
        docs_service = build('docs', 'v1', credentials=credentials)
        sheets_service = build('sheets', 'v4', credentials=credentials)
        
        logger.info("Successfully created all Workspace API clients")
        return {
            'gmail': gmail_service,
            'calendar': calendar_service,
            'drive': drive_service,
            'docs': docs_service,
            'sheets': sheets_service
        }
        
    except Exception as e:
        logger.error(f"Failed to create Workspace clients: {e}")
        return {}

def fetch_calendar_events(calendar_service, days_ahead=7):
    """Fetch upcoming calendar events"""
    if not calendar_service:
        return []
    
    try:
        # Get events for the next 7 days
        now = datetime.utcnow()
        end_time = now + timedelta(days=days_ahead)
        
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format events for AI processing
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            location = event.get('location', '')
            
            formatted_events.append({
                'title': summary,
                'start_time': start,
                'location': location,
                'description': event.get('description', '')[:200]  # Limit description length
            })
        
        logger.info(f"Fetched {len(formatted_events)} calendar events")
        return formatted_events
        
    except Exception as e:
        logger.error(f"Failed to fetch calendar events: {e}")
        return []

def fetch_recent_emails(gmail_service, max_results=5):
    """Fetch recent emails from Gmail"""
    if not gmail_service:
        return []
    
    try:
        # Get recent messages
        results = gmail_service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q='is:unread OR newer_than:1d'  # Unread or from last day
        ).execute()
        
        messages = results.get('messages', [])
        
        formatted_emails = []
        for message in messages:
            try:
                msg = gmail_service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata'
                ).execute()
                
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown date')
                
                formatted_emails.append({
                    'subject': subject[:100],  # Limit subject length
                    'sender': sender[:50],     # Limit sender length
                    'date': date,
                    'snippet': msg.get('snippet', '')[:200]  # Limit snippet length
                })
                
            except Exception as e:
                logger.warning(f"Failed to process email {message['id']}: {e}")
                continue
        
        logger.info(f"Fetched {len(formatted_emails)} recent emails")
        return formatted_emails
        
    except Exception as e:
        logger.error(f"Failed to fetch recent emails: {e}")
        return []

def fetch_recent_drive_files(drive_service, max_results=10):
    """Fetch recent Drive files"""
    if not drive_service:
        return []
    
    try:
        # Get recent files
        results = drive_service.files().list(
            pageSize=max_results,
            orderBy='modifiedTime desc',
            fields="files(id,name,mimeType,modifiedTime,owners,webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        
        formatted_files = []
        for file in files:
            # Skip certain file types that aren't useful for context
            mime_type = file.get('mimeType', '')
            if 'folder' in mime_type or 'shortcut' in mime_type:
                continue
                
            owners = file.get('owners', [])
            owner_name = owners[0].get('displayName', 'Unknown') if owners else 'Unknown'
            
            formatted_files.append({
                'name': file.get('name', 'Untitled')[:50],  # Limit name length
                'type': get_file_type_description(mime_type),
                'modified': file.get('modifiedTime', 'Unknown date'),
                'owner': owner_name,
                'link': file.get('webViewLink', '')
            })
        
        logger.info(f"Fetched {len(formatted_files)} recent Drive files")
        return formatted_files
        
    except Exception as e:
        logger.error(f"Failed to fetch Drive files: {e}")
        return []

def get_file_type_description(mime_type):
    """Convert MIME type to human-readable description"""
    type_map = {
        'application/vnd.google-apps.document': 'Google Doc',
        'application/vnd.google-apps.spreadsheet': 'Google Sheet',
        'application/vnd.google-apps.presentation': 'Google Slides',
        'application/pdf': 'PDF',
        'image/': 'Image',
        'text/': 'Text file',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel file'
    }
    
    for key, description in type_map.items():
        if key in mime_type:
            return description
    
    return 'File'

@functions_framework.http
def multimodal_agent_orchestrator(request):
    """
    Advanced multimodal AI agent powered by Gemini 1.5 Pro
    Handles text, audio, and image inputs with intelligent, contextual responses
    """
    if request.method != 'POST':
        return 'Method Not Allowed', 405

    try:
        if not SERVICES_AVAILABLE:
            return jsonify({
                "status": "error",
                "message": "AI services temporarily unavailable"
            }), 503

        # Get input from various sources
        audio_file = request.files.get('audio_file')
        text_command = request.form.get('text_command') or request.form.get('voice_command')
        image_file = request.files.get('image_file')
        
        # Authentication tokens
        auth_code = request.form.get('auth_code')
        id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        logger.info(f"Request received - Audio: {audio_file is not None}, Text: {bool(text_command)}, Image: {image_file is not None}")
        
        # Validate ID token for secure function invocation
        if id_token:
            user_id = validate_id_token(id_token)
            if not user_id:
                logger.error("Invalid or expired ID token.")
                return jsonify({
                    "status": "error",
                    "message": "Authentication failed: Invalid or expired session."
                }), 401
            logger.info(f"ID token validated for user: {user_id}")
        else:
            logger.warning("No ID token provided in the request.")
            # Depending on your security policy, you might want to return 401 here
            # For now, we proceed but log the absence of the token.

        # Validate required inputs
        if not auth_code:
            logger.error("Missing required 'auth_code' in request.")
            return jsonify({
                "status": "error",
                "message": "Authentication code is missing. Please ensure you are signed in."
            }), 400

        # Process inputs to get user query
        user_query = None
        image_data = None
        
        audio_data = None
        image_data = None
        audio_path = None
        image_path = None

        try:
            # Save files to a temporary directory for processing
            # Cloud Functions provide a writable /tmp directory
            temp_dir = tempfile.gettempdir()

            if audio_file:
                audio_path = os.path.join(temp_dir, secure_filename(audio_file.filename))
                audio_file.save(audio_path)
                logger.info(f"Audio file saved to {audio_path}")
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()

            if image_file:
                image_path = os.path.join(temp_dir, secure_filename(image_file.filename))
                image_file.save(image_path)
                logger.info(f"Image file saved to {image_path}")
                with open(image_path, 'rb') as f:
                    image_data = f.read()

            # Process inputs to get user query
            user_query = None
            if audio_data:
                logger.info("Processing audio input...")
                try:
                    user_query = transcribe_audio_advanced(audio_data)
                    logger.info(f"Transcribed: {user_query}")
                except Exception as e:
                    logger.error(f"Audio transcription failed: {e}")
                    user_query = "I heard your voice but couldn't understand it clearly."
            elif text_command:
                logger.info("Processing text input...")
                user_query = text_command

            # Validate we have some input
            if not user_query:
                return jsonify({
                    "status": "error",
                    "message": "No valid input provided. Please send text, audio, or both."
                }), 400

            # Get user context (simplified for now, full workspace integration coming)
            user_context = get_user_context(auth_code, id_token)

            # Generate intelligent response using Gemini 1.5 Pro
            try:
                response_text = generate_intelligent_response(
                    user_query=user_query,
                    image_data=image_data,
                    user_context=user_context
                )
            except Exception as e:
                logger.error(f"Gemini response generation failed: {e}")
                response_text = f"I understand you said '{user_query}'. I'm processing your request with my advanced AI capabilities, but encountered a technical issue. Let me help you with a thoughtful response instead."

            # Generate high-quality audio response
            try:
                response_audio = synthesize_speech(response_text, voice_type="standard")
                if response_audio and len(response_audio) > 0:
                    return response_audio, 200, {
                        'Content-Type': 'audio/mpeg',
                        'X-Response-Length': str(len(response_text)),
                        'X-AI-Model': 'gemini-1.5-pro'
                    }
            except Exception as e:
                logger.error(f"Speech synthesis failed: {e}")

            # Fallback to JSON response if audio synthesis fails
            return jsonify({
                "status": "success",
                "response": response_text,
                "ai_model": "gemini-1.5-pro",
                "input_type": "audio" if audio_file else "text",
                "message": "Audio synthesis temporarily unavailable, returning text response"
            }), 200

        except Exception as e:
            logger.error(f"Critical error in orchestrator: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": "I encountered an unexpected error while processing your request. Please try again."
            }), 500
        finally:
            # Clean up temporary files
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Cleaned up audio file: {audio_path}")
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"Cleaned up image file: {image_path}")

def transcribe_audio_advanced(audio_data):
    """Advanced audio transcription with multiple encoding support"""
    try:
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_data)
        logger.info(f"Received audio data for transcription: {len(audio_data)} bytes")
        
        # Advanced configuration for better accuracy
        configs_to_try = [
            # AMR format (from Android MediaRecorder)
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.AMR,
                sample_rate_hertz=8000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_confidence=True,
                model="latest_long"
            ),
            # Fallback to auto-detection
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_confidence=True,
                model="latest_long"
            )
        ]
        
        for config in configs_to_try:
            try:
                response = client.recognize(config=config, audio=audio)
                if response.results and response.results[0].alternatives:
                    transcript = response.results[0].alternatives[0].transcript
                    confidence = response.results[0].alternatives[0].confidence
                    logger.info(f"Transcription confidence: {confidence}")
                    return transcript.strip()
            except Exception as e:
                logger.warning(f"Transcription attempt failed: {e}")
                continue
        
        return "I heard you speaking but couldn't transcribe it clearly. Could you please repeat that?"
        
    except Exception as e:
        logger.error(f"Critical transcription error: {e}")
        return "I'm having trouble processing your audio right now."

def get_user_context(auth_code, id_token):
    """Get comprehensive user context from Google Workspace integration"""
    context = {
        "user_authenticated": bool(auth_code and id_token),
        "timestamp": "current_time", 
        "session": "active"
    }
    
    # Enhanced context with Google Workspace data
    if auth_code:
        try:
            workspace_clients = get_workspace_clients(auth_code)
            
            # Fetch calendar events for the next few days
            context["calendar_events"] = fetch_calendar_events(workspace_clients.get('calendar'))
            
            # Fetch recent emails
            context["recent_emails"] = fetch_recent_emails(workspace_clients.get('gmail'))
            
            # Fetch recent Drive files
            context["recent_files"] = fetch_recent_drive_files(workspace_clients.get('drive'))
            
            # Add current time context
            context["current_time"] = datetime.utcnow().isoformat() + 'Z'
            context["timezone"] = "UTC"
            
            logger.info("Successfully enriched context with Workspace data")
            
        except Exception as e:
            logger.warning(f"Failed to fetch Workspace context: {e}")
            context["workspace_error"] = "Could not access your Google Workspace data"
    
    return context

def generate_intelligent_response(user_query, image_data=None, user_context=None):
    """Generate intelligent, contextual responses using Gemini 1.5 Pro"""
    try:
        # Initialize the most powerful Gemini model
        model = GenerativeModel("gemini-1.5-pro-001")
        
        # Create a sophisticated system prompt
        system_prompt = """You are a powerful, personal AI assistant - think of yourself as a highly capable, intelligent companion. You speak naturally like a real person would, not like a robot.

Your personality:
- Conversational, friendly, and engaging 
- Confident and knowledgeable, but not arrogant
- Proactive in offering help and suggestions
- You remember context and build on previous interactions
- You speak directly and naturally, avoiding robotic phrases

Your capabilities:
- Access to the user's calendar, emails, and personal context
- Can analyze images, understand speech, and provide insights
- Help with productivity, scheduling, research, and problem-solving
- Current knowledge and real-time information access
- Google Workspace integration (Calendar, Gmail, Drive, Docs, Sheets)

Communication style:
- Speak like you're talking to a friend or colleague
- Be direct and helpful, not overly formal
- Use "I" statements naturally ("I see you have...", "I can help with...")
- No need to say "I'm an AI" or similar disclaimers
- Be proactive and suggest next steps

The user trusts you with their data and expects powerful, intelligent assistance."""

        # Build the prompt parts
        prompt_parts = [system_prompt]
        
        # Add user query
        if user_query:
            prompt_parts.append(f"User request: {user_query}")
        
        # Add image if provided
        if image_data:
            try:
                image_part = Part.from_data(data=image_data, mime_type="image/jpeg")
                prompt_parts.append(image_part)
                prompt_parts.append("Please analyze the attached image as part of your response.")
            except Exception as e:
                logger.error(f"Failed to add image to prompt: {e}")
        
        # Add context
        if user_context and user_context.get("user_authenticated"):
            prompt_parts.append("Note: The user is authenticated and this is a secure, personal interaction.")
            
            # Add calendar context if available
            if user_context.get("calendar_events"):
                calendar_context = "Current calendar events:\n"
                for event in user_context["calendar_events"]:
                    calendar_context += f"- {event['title']} at {event['start_time']}"
                    if event.get('location'):
                        calendar_context += f" (Location: {event['location']})"
                    calendar_context += "\n"
                prompt_parts.append(calendar_context)
            
            # Add email context if available
            if user_context.get("recent_emails"):
                email_context = "Recent emails:\n"
                for email in user_context["recent_emails"]:
                    email_context += f"- From {email['sender']}: {email['subject']}\n"
                    if email.get('snippet'):
                        email_context += f"  Preview: {email['snippet']}\n"
                prompt_parts.append(email_context)
            
            # Add Drive files context if available
            if user_context.get("recent_files"):
                files_context = "Recent Drive files:\n"
                for file in user_context["recent_files"]:
                    files_context += f"- {file['name']} ({file['type']}) - Modified: {file['modified']}\n"
                prompt_parts.append(files_context)
            
            # Add time context if available
            if user_context.get("current_time"):
                time_context = f"Current time: {user_context['current_time']}"
                prompt_parts.append(time_context)
            
            # Add comprehensive workspace integration note
            workspace_features = []
            if user_context.get("calendar_events"):
                workspace_features.append("calendar events")
            if user_context.get("recent_emails"):
                workspace_features.append("recent emails")
            if user_context.get("recent_files"):
                workspace_features.append("Drive files")
            
            if workspace_features:
                integration_note = f"You have access to the user's {', '.join(workspace_features)}. Use this information to provide personalized, contextually relevant responses. You can reference specific events, emails, or files when relevant to help with productivity, scheduling, and task management."
                prompt_parts.append(integration_note)
        
        # Configure generation settings for high-quality responses
        generation_config = GenerationConfig(
            temperature=0.7,  # Balanced creativity and accuracy
            top_p=0.9,
            top_k=40,
            max_output_tokens=1500,  # Allow for detailed responses
        )
        
        # Safety settings - allow for helpful responses
        safety_settings = [
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
            SafetySetting(
                category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            ),
        ]
        
        # Generate response
        response = model.generate_content(
            prompt_parts,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        if response and response.text:
            return response.text.strip()
        else:
            return f"I understand you said '{user_query}'. I'm here to help! Could you tell me more about what you need assistance with?"
            
    except Exception as e:
        logger.error(f"Gemini generation error: {e}")
        # Provide an intelligent fallback response
        if "hello" in user_query.lower():
            return "Hello! I'm your personal AI assistant, powered by advanced AI. I can help you with questions, analyze images, process voice commands, and assist with various tasks. What would you like to do today?"
        elif any(word in user_query.lower() for word in ["help", "what", "how"]):
            return f"I understand you're asking: '{user_query}'. I'm your intelligent AI assistant with multimodal capabilities. I can help you with information, analyze images, answer questions, and assist with productivity tasks. What specific information do you need?"
        else:
            return f"I heard you say '{user_query}'. I'm your advanced AI assistant, ready to help with whatever you need. Could you tell me more about how I can assist you today?"

def synthesize_speech(text_to_speak, voice_type="standard"):
    """Generate high-quality speech using premium or standard voices based on voice_type."""
    try:
        client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
        
        if voice_type == "premium":
            voice_name = "en-US-Neural2-J"  # Premium Neural2 voice
            speaking_rate = 1.1
            sample_rate = 24000
        else:  # Default to standard voice for cost optimization
            voice_name = "en-US-Standard-J"  # Standard voice
            speaking_rate = 1.0
            sample_rate = 16000 # Standard sample rate
            
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=0.0,
            volume_gain_db=0.0,
            sample_rate_hertz=sample_rate
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        if response.audio_content:
            logger.info(f"Generated {len(response.audio_content)} bytes of {voice_type} audio")
            return response.audio_content
        else:
            logger.error("No audio content generated")
            return None
            
    except Exception as e:
        logger.error(f"Speech synthesis failed for voice type {voice_type}: {e}")
        return None

# For local testing
if __name__ == "__main__":
    import functions_framework
    app = functions_framework.create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)