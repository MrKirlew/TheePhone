# main_conversational.py - Enhanced Gemini Backend with Conversational AI
import functions_framework
from werkzeug.utils import secure_filename
import os
import tempfile
import json
import logging
from flask import jsonify
import base64
from typing import Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import conversational AI system
from conversational_ai import ConversationalAI, enhance_gemini_prompt

# Import Google Cloud libraries
try:
    from google.cloud import speech
    from google.cloud import texttospeech
    from google.cloud import secretmanager
    from google.cloud import firestore
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, SafetySetting, GenerationConfig
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    import google.auth
    from datetime import datetime, timedelta
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Required libraries not available: {e}")
    SERVICES_AVAILABLE = False

# Initialize services
if SERVICES_AVAILABLE:
    try:
        vertexai.init(project="twothreeatefi", location="us-central1")
        db = firestore.Client()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        db = None

# Global conversational AI instances (in production, use proper session management)
user_sessions = {}

def get_or_create_session(user_id: str) -> ConversationalAI:
    """Get or create a conversational AI session for a user"""
    if user_id not in user_sessions:
        user_sessions[user_id] = ConversationalAI()
        # Load user history from Firestore if available
        if db:
            try:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    # Restore user profile
                    if 'profile' in user_data:
                        user_sessions[user_id].memory.user_profile.update(user_data['profile'])
                    # Restore conversation history
                    if 'conversation_history' in user_data:
                        for interaction in user_data['conversation_history'][-20:]:  # Last 20 interactions
                            user_sessions[user_id].memory.add_interaction(
                                interaction.get('user_input', ''),
                                interaction.get('ai_response', ''),
                                interaction.get('metadata', {})
                            )
            except Exception as e:
                logger.error(f"Failed to load user session: {e}")
    
    return user_sessions[user_id]

def save_user_session(user_id: str, conversational_ai: ConversationalAI):
    """Save user session to Firestore"""
    if not db:
        return
        
    try:
        # Prepare data for storage
        user_data = {
            'profile': conversational_ai.memory.user_profile,
            'relationship_context': conversational_ai.memory.relationship_context,
            'conversation_history': list(conversational_ai.memory.long_term_memory),
            'last_updated': datetime.utcnow()
        }
        
        # Save to Firestore
        db.collection('users').document(user_id).set(user_data, merge=True)
        logger.info(f"Saved session for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save user session: {e}")

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
        
        name = f"projects/{project_id}/secrets/oauth-web-client-secret/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return json.loads(response.payload.data.decode("UTF-8"))
    except Exception as e:
        logger.error(f"Failed to get web client secrets: {e}")
        return {
            "web": {
                "client_id": "843267258954-mc04n5od104s75to3umjl46rva3p0r0s.apps.googleusercontent.com",
                "client_secret": "placeholder-secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }

def get_workspace_clients(auth_code):
    """Exchange authorization code for credentials and return API clients"""
    try:
        client_config = get_web_client_secrets()
        flow = Flow.from_client_config(client_config, scopes=WORKSPACE_SCOPES)
        flow.redirect_uri = 'postmessage'
        
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
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No title')
            location = event.get('location', '')
            
            formatted_events.append({
                'title': summary,
                'start_time': start,
                'location': location,
                'description': event.get('description', '')[:200]
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
        results = gmail_service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q='is:unread OR newer_than:1d'
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
                    'subject': subject[:100],
                    'sender': sender[:50],
                    'date': date,
                    'snippet': msg.get('snippet', '')[:200]
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
        results = drive_service.files().list(
            pageSize=max_results,
            orderBy='modifiedTime desc',
            fields="files(id,name,mimeType,modifiedTime,owners,webViewLink)"
        ).execute()
        
        files = results.get('files', [])
        
        formatted_files = []
        for file in files:
            mime_type = file.get('mimeType', '')
            if 'folder' in mime_type or 'shortcut' in mime_type:
                continue
                
            owners = file.get('owners', [])
            owner_name = owners[0].get('displayName', 'Unknown') if owners else 'Unknown'
            
            formatted_files.append({
                'name': file.get('name', 'Untitled')[:50],
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
def conversational_agent(request):
    """
    Enhanced conversational AI agent powered by Gemini 1.5 Pro
    with memory, reasoning, and personality
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
        id_token = request.form.get('id_token')
        
        # Extract user ID from token or use default
        user_id = "default_user"
        if id_token:
            try:
                # In production, properly decode and validate the ID token
                import hashlib
                user_id = hashlib.md5(id_token.encode()).hexdigest()[:16]
            except:
                pass
        
        logger.info(f"Request from user {user_id} - Audio: {audio_file is not None}, Text: {bool(text_command)}, Image: {image_file is not None}")
        
        # Get or create conversational AI session
        conversational_ai = get_or_create_session(user_id)
        
        # Process inputs to get user query
        user_query = None
        image_data = None
        
        # Process audio if provided
        if audio_file:
            logger.info("Processing audio input...")
            try:
                audio_data = audio_file.read()
                user_query = transcribe_audio_advanced(audio_data)
                logger.info(f"Transcribed: {user_query}")
            except Exception as e:
                logger.error(f"Audio transcription failed: {e}")
                user_query = "I heard your voice but couldn't understand it clearly."
                
        # Use text command if no audio or if audio transcription failed
        elif text_command:
            logger.info("Processing text input...")
            user_query = text_command
            
        # Process image if provided
        if image_file:
            logger.info("Processing image input...")
            try:
                image_data = image_file.read()
                logger.info(f"Image received: {len(image_data)} bytes")
            except Exception as e:
                logger.error(f"Image processing failed: {e}")
        
        # Validate we have some input
        if not user_query:
            return jsonify({
                "status": "error",
                "message": "No valid input provided. Please send text, audio, or both."
            }), 400
        
        # Get user context
        user_context = get_user_context(auth_code, id_token)
        
        # Generate intelligent response using enhanced Gemini
        try:
            response_text = generate_enhanced_response(
                user_query=user_query,
                image_data=image_data,
                user_context=user_context,
                conversational_ai=conversational_ai
            )
            
            # Save user session
            save_user_session(user_id, conversational_ai)
            
        except Exception as e:
            logger.error(f"Enhanced response generation failed: {e}")
            # Fallback to conversational AI without Gemini
            response_text, _ = conversational_ai.generate_response(user_query, user_context)
        
        # Generate high-quality audio response
        try:
            response_audio = synthesize_premium_speech(response_text)
            if response_audio and len(response_audio) > 0:
                return response_audio, 200, {
                    'Content-Type': 'audio/mpeg',
                    'X-Response-Length': str(len(response_text)),
                    'X-AI-Model': 'gemini-1.5-pro-conversational',
                    'X-User-Session': user_id
                }
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
        
        # Fallback to JSON response if audio synthesis fails
        return jsonify({
            "status": "success",
            "response": response_text,
            "ai_model": "gemini-1.5-pro-conversational",
            "input_type": "audio" if audio_file else "text",
            "session_id": user_id,
            "message": "Audio synthesis temporarily unavailable, returning text response"
        }), 200
            
    except Exception as e:
        logger.error(f"Critical error in conversational agent: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "I encountered an unexpected error while processing your request. Please try again."
        }), 500

def transcribe_audio_advanced(audio_data):
    """Advanced audio transcription with multiple encoding support"""
    try:
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_data)
        
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
        "timestamp": datetime.utcnow().isoformat(),
        "session": "active"
    }
    
    # Enhanced context with Google Workspace data
    if auth_code:
        try:
            workspace_clients = get_workspace_clients(auth_code)
            
            # Fetch calendar events
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

def generate_enhanced_response(user_query, image_data=None, user_context=None, conversational_ai=None):
    """Generate intelligent, contextual responses using enhanced Gemini 1.5 Pro"""
    try:
        # Initialize the most powerful Gemini model
        model = GenerativeModel("gemini-1.5-pro-001")
        
        # Get enhanced prompt with conversational context
        enhanced_prompt = enhance_gemini_prompt(user_query, user_context or {}, conversational_ai)
        
        # Build the prompt parts
        prompt_parts = [enhanced_prompt]
        
        # Add user query context
        prompt_parts.append(f"\nCurrent query: {user_query}")
        
        # Add image if provided
        if image_data:
            try:
                image_part = Part.from_data(data=image_data, mime_type="image/jpeg")
                prompt_parts.append(image_part)
                prompt_parts.append("Analyze the attached image as part of your response.")
            except Exception as e:
                logger.error(f"Failed to add image to prompt: {e}")
        
        # Add workspace context if available
        if user_context and user_context.get("user_authenticated"):
            workspace_context = []
            
            if user_context.get("calendar_events"):
                workspace_context.append(f"Calendar: {len(user_context['calendar_events'])} upcoming events")
                
            if user_context.get("recent_emails"):
                workspace_context.append(f"Email: {len(user_context['recent_emails'])} recent messages")
                
            if user_context.get("recent_files"):
                workspace_context.append(f"Drive: {len(user_context['recent_files'])} recent files")
                
            if workspace_context:
                prompt_parts.append(f"\nWorkspace context: {', '.join(workspace_context)}")
        
        # Configure generation settings for conversational responses
        generation_config = GenerationConfig(
            temperature=0.8,  # Slightly higher for more natural conversation
            top_p=0.95,
            top_k=40,
            max_output_tokens=1000,  # Reasonable length for conversation
        )
        
        # Safety settings
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
            # Store the interaction in conversational memory
            final_response = response.text.strip()
            conversational_ai.memory.add_interaction(user_query, final_response, {
                "model": "gemini-1.5-pro",
                "context": user_context,
                "had_image": image_data is not None
            })
            return final_response
        else:
            # Fallback to conversational AI
            fallback_response, _ = conversational_ai.generate_response(user_query, user_context)
            return fallback_response
            
    except Exception as e:
        logger.error(f"Gemini generation error: {e}")
        # Use conversational AI as fallback
        if conversational_ai:
            fallback_response, _ = conversational_ai.generate_response(user_query, user_context)
            return fallback_response
        else:
            return "I'm having a technical issue right now, but I'm still here to help. Could you please rephrase your question?"

def synthesize_premium_speech(text_to_speak):
    """Generate high-quality speech using premium voices"""
    try:
        client = texttospeech.TextToSpeechClient()
        
        # Configure input
        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
        
        # Use premium Neural2 voice for natural, human-like speech
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-J",  # Premium Neural2 voice
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        # High-quality audio configuration
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.1,  # Slightly faster for efficiency
            pitch=0.0,
            volume_gain_db=0.0,
            sample_rate_hertz=24000  # High-quality audio
        )
        
        # Generate speech
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        if response.audio_content:
            logger.info(f"Generated {len(response.audio_content)} bytes of premium audio")
            return response.audio_content
        else:
            logger.error("No audio content generated")
            return None
            
    except Exception as e:
        logger.error(f"Premium speech synthesis failed: {e}")
        # Try fallback with standard voice
        try:
            return synthesize_fallback_speech(text_to_speak)
        except Exception as fallback_error:
            logger.error(f"Fallback speech synthesis also failed: {fallback_error}")
            return None

def synthesize_fallback_speech(text_to_speak):
    """Fallback speech synthesis with standard voice"""
    try:
        client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
        
        # Standard voice as fallback
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Standard-J",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
        
    except Exception as e:
        logger.error(f"Fallback speech synthesis failed: {e}")
        return None

# For local testing
if __name__ == "__main__":
    import functions_framework
    app = functions_framework.create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)