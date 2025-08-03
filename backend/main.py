# main_powerful_ai.py - Production-Grade Gemini 1.5 Pro Multimodal AI Agent
import functions_framework
from werkzeug.utils import secure_filename
import os
import tempfile
import json
import logging
from flask import jsonify
import base64
import hashlib
from datetime import datetime, timedelta

# Set up structured logging for debugging
import sys
import json
from datetime import datetime

class StructuredLogger:
    """Enhanced logger for debugging AI agent reasoning and API interactions"""
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create console handler with structured format
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        # Custom formatter for structured logs
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    def log_reasoning_step(self, step_name, details, user_query=None, session_id=None):
        """Log AI reasoning steps with context"""
        log_data = {
            "type": "reasoning_step",
            "step": step_name,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "user_query": user_query[:100] if user_query else None
        }
        self.logger.info(f"REASONING: {json.dumps(log_data, default=str)}")
    
    def log_api_interaction(self, api_name, operation, result_summary, latency_ms=None, session_id=None):
        """Log API interactions with performance metrics"""
        log_data = {
            "type": "api_interaction",
            "api": api_name,
            "operation": operation,
            "result": result_summary,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id
        }
        self.logger.info(f"API: {json.dumps(log_data, default=str)}")
    
    def log_intent_detection(self, user_query, detected_intent, confidence=None, apis_needed=None, session_id=None):
        """Log intent detection results"""
        log_data = {
            "type": "intent_detection",
            "user_query": user_query[:200] if user_query else None,
            "detected_intent": detected_intent,
            "confidence": confidence,
            "apis_needed": apis_needed,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id
        }
        self.logger.info(f"INTENT: {json.dumps(log_data, default=str)}")
    
    def log_function_call(self, function_name, parameters, result_summary, success=True, session_id=None):
        """Log Gemini function calls"""
        log_data = {
            "type": "function_call",
            "function": function_name,
            "parameters": parameters,
            "result": result_summary,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id
        }
        self.logger.info(f"FUNCTION: {json.dumps(log_data, default=str)}")
    
    def log_conversation_turn(self, user_input, ai_response, context_used, session_id=None):
        """Log complete conversation turns"""
        log_data = {
            "type": "conversation_turn",
            "user_input": user_input[:200] if user_input else None,
            "ai_response": ai_response[:200] if ai_response else None,
            "context_keys": list(context_used.keys()) if context_used else [],
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id
        }
        self.logger.info(f"CONVERSATION: {json.dumps(log_data, default=str)}")
    
    def info(self, message):
        """Standard info logging"""
        self.logger.info(message)
    
    def error(self, message, exc_info=False):
        """Standard error logging"""
        self.logger.error(message, exc_info=exc_info)
    
    def warning(self, message):
        """Standard warning logging"""
        self.logger.warning(message)
    
    def debug(self, message):
        """Standard debug logging"""
        self.logger.debug(message)

# Initialize structured logger
logger = StructuredLogger(__name__)

# Import Google Cloud libraries
try:
    from google.cloud import speech
    from google.cloud import texttospeech
    from google.cloud import secretmanager
    from google.cloud import vision
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, SafetySetting, GenerationConfig
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import Flow
    import google.auth
    from datetime import datetime, timedelta
    
    # Import enhanced services
    from enhanced_services import EnhancedGoogleServices, enhance_user_context
    
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
        # Fallback configuration for testing
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

def fetch_calendar_events(calendar_service, days_ahead=7, today_only=False):
    """Fetch upcoming calendar events"""
    if not calendar_service:
        return []
    
    try:
        # Get events for the next 7 days or just today
        now = datetime.utcnow()
        
        if today_only:
            # For "today" queries, get events from start of today to end of today
            start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_today = start_of_today + timedelta(days=1)
            time_min = start_of_today.isoformat() + 'Z'
            time_max = end_of_today.isoformat() + 'Z'
            max_results = 20  # Show more events for today
        else:
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            max_results = 10
        
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
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
            
            # Parse the start time to make it more readable
            try:
                from dateutil import parser
                start_dt = parser.parse(start)
                if start_dt.time() != datetime.min.time():
                    # It's a timed event
                    start_formatted = start_dt.strftime('%I:%M %p')
                else:
                    # It's an all-day event
                    start_formatted = 'All day'
            except:
                start_formatted = start
            
            formatted_events.append({
                'title': summary,
                'start_time': start,
                'start_time_formatted': start_formatted,
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

# Global conversation memory storage (in production, use Redis or Cloud Firestore)
conversation_memory = {}

class ConversationMemory:
    """Manages conversation history with context caching"""
    
    def __init__(self, max_history=20, max_age_hours=24):
        self.max_history = max_history
        self.max_age_hours = max_age_hours
    
    def get_session_id(self, user_id, session_info=None):
        """Generate a consistent session ID for the user"""
        if session_info:
            # Use additional session info if available
            session_data = f"{user_id}_{session_info}"
        else:
            session_data = user_id
        return hashlib.md5(session_data.encode()).hexdigest()[:16]
    
    def add_message(self, session_id, role, content, timestamp=None):
        """Add a message to conversation history"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        if session_id not in conversation_memory:
            conversation_memory[session_id] = {
                'messages': [],
                'created_at': timestamp,
                'last_active': timestamp
            }
        
        conversation_memory[session_id]['messages'].append({
            'role': role,
            'content': content,
            'timestamp': timestamp.isoformat()
        })
        
        conversation_memory[session_id]['last_active'] = timestamp
        
        # Keep only recent messages
        if len(conversation_memory[session_id]['messages']) > self.max_history:
            conversation_memory[session_id]['messages'] = conversation_memory[session_id]['messages'][-self.max_history:]
    
    def get_conversation_history(self, session_id):
        """Get formatted conversation history for Gemini"""
        if session_id not in conversation_memory:
            return []
        
        # Clean up old conversations
        cutoff_time = datetime.utcnow() - timedelta(hours=self.max_age_hours)
        if conversation_memory[session_id]['last_active'] < cutoff_time:
            del conversation_memory[session_id]
            return []
        
        messages = conversation_memory[session_id]['messages']
        formatted_history = []
        
        for msg in messages[-self.max_history:]:  # Keep recent messages
            formatted_history.append(f"{msg['role'].title()}: {msg['content']}")
        
        return formatted_history
    
    def clear_session(self, session_id):
        """Clear conversation history for a session"""
        if session_id in conversation_memory:
            del conversation_memory[session_id]

# Initialize conversation memory
conv_memory = ConversationMemory()

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

    session_id = None
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
        
        # Advanced command mode
        advanced_command = request.form.get('advanced_command')
        
        # Get session ID early for logging
        user_id = id_token if id_token else "anonymous_user"
        session_id = conv_memory.get_session_id(user_id)
        
        logger.log_reasoning_step(
            "request_received",
            {
                "has_audio": audio_file is not None,
                "has_text": bool(text_command),
                "has_image": image_file is not None,
                "has_advanced": bool(advanced_command),
                "is_authenticated": bool(auth_code and id_token)
            },
            session_id=session_id
        )
        
        # Process inputs to get user query
        user_query = None
        image_data = None
        
        # Process audio if provided
        if audio_file:
            logger.log_reasoning_step("audio_processing_start", {"file_size_bytes": len(audio_file.read())}, session_id=session_id)
            audio_file.seek(0)  # Reset file pointer
            try:
                start_time = datetime.utcnow()
                audio_data = audio_file.read()
                user_query = transcribe_audio_advanced(audio_data)
                end_time = datetime.utcnow()
                latency_ms = (end_time - start_time).total_seconds() * 1000
                
                logger.log_api_interaction(
                    "speech_recognition",
                    "transcribe_audio",
                    f"Successfully transcribed: '{user_query[:50]}...' ({len(user_query)} chars)",
                    latency_ms,
                    session_id
                )
                logger.log_reasoning_step("audio_transcription_success", {"transcribed_text": user_query}, user_query, session_id)
            except Exception as e:
                logger.error(f"Audio transcription failed: {e}")
                logger.log_reasoning_step("audio_transcription_failed", {"error": str(e)}, session_id=session_id)
                user_query = "I heard your voice but couldn't understand it clearly."
                
        # Use text command if no audio or if audio transcription failed
        elif text_command:
            logger.log_reasoning_step("text_input_processing", {"text_length": len(text_command)}, text_command, session_id)
            user_query = text_command
            
        # Use advanced command if provided
        elif advanced_command:
            logger.log_reasoning_step("advanced_command_processing", {"command_length": len(advanced_command)}, advanced_command, session_id)
            user_query = advanced_command
            
        # Process image if provided
        if image_file:
            logger.info("Processing image input...")
            try:
                image_data = image_file.read()
                logger.info(f"Image received: {len(image_data)} bytes")
                
                # Analyze image with Vision API
                try:
                    vision_service = EnhancedGoogleServices()
                    vision_analysis = vision_service.analyze_image(image_data)
                    
                    # Add vision analysis to user context
                    if 'vision_analysis' not in user_context:
                        user_context['vision_analysis'] = vision_analysis
                    
                    # If no text query provided, create one based on image analysis
                    if not user_query and vision_analysis.get('text'):
                        user_query = f"Please analyze this image. I can see it contains: {vision_analysis['text'][:200]}..."
                    elif not user_query:
                        user_query = "Please analyze this image and tell me what you see."
                        
                    logger.info("Vision API analysis completed")
                except Exception as e:
                    logger.warning(f"Vision API analysis failed: {e}")
                    if not user_query:
                        user_query = "Please analyze this image."
                        
            except Exception as e:
                logger.error(f"Image processing failed: {e}")
        
        # Validate we have some input
        if not user_query:
            return jsonify({
                "status": "error",
                "message": "No valid input provided. Please send text, audio, or both."
            }), 400
        
        # Get conversation history
        conversation_history = conv_memory.get_conversation_history(session_id)
        logger.log_reasoning_step(
            "conversation_context_loaded",
            {
                "session_id": session_id,
                "history_length": len(conversation_history),
                "user_authenticated": bool(id_token)
            },
            user_query,
            session_id
        )
        
        # Get user context (simplified for now, full workspace integration coming)
        user_context = get_user_context(auth_code, id_token, user_query)
        user_context['conversation_history'] = conversation_history
        user_context['session_id'] = session_id
        user_context['auth_code'] = auth_code  # Store for function calling
        
        # Use enhanced intent detection for all queries to understand user needs
        try:
            # Import enhanced intent detector
            from enhanced_intent_detector import EnhancedIntentDetector
            intent_detector = EnhancedIntentDetector()
            
            # Detect intent and required API actions
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            start_time = datetime.utcnow()
            intent_data = loop.run_until_complete(intent_detector.detect_intent_and_actions(user_query))
            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log intent detection results
            logger.log_intent_detection(
                user_query,
                intent_data.get('detected_intents', []),
                intent_data.get('confidence'),
                list(intent_data.get('apis', {}).keys()) if intent_data.get('apis') else [],
                session_id
            )
            
            # Add intent info to context
            user_context['is_greeting'] = intent_data.get('is_greeting', False)
            user_context['is_casual_conversation'] = intent_data.get('is_casual_conversation', False)
            
            if intent_data.get('needs_api_data', False):
                # For now, use the existing workspace data if available
                # The actual API calls are already made in get_user_context
                if 'calendar' in intent_data.get('apis', {}):
                    logger.log_reasoning_step("intent_calendar_detected", {"apis_needed": list(intent_data.get('apis', {}).keys())}, user_query, session_id)
                    user_context['user_asking_about'] = 'calendar'
                elif 'email' in intent_data.get('apis', {}):
                    logger.log_reasoning_step("intent_email_detected", {"apis_needed": list(intent_data.get('apis', {}).keys())}, user_query, session_id)
                    user_context['user_asking_about'] = 'email'
                elif 'drive' in intent_data.get('apis', {}) or 'docs' in intent_data.get('apis', {}) or 'sheets' in intent_data.get('apis', {}):
                    logger.log_reasoning_step("intent_documents_detected", {"apis_needed": list(intent_data.get('apis', {}).keys())}, user_query, session_id)
                    user_context['user_asking_about'] = 'documents'
                    
                # Add intent reasoning to context
                user_context['intent_reasoning'] = intent_data.get('reasoning', '')
        except Exception as e:
            logger.error(f"Enhanced intent detection failed: {e}")
            logger.log_reasoning_step("intent_detection_failed", {"error": str(e), "fallback_used": True}, user_query, session_id)
            # Fall back to simple keyword detection
            query_lower = user_query.lower() if user_query else ""
            if any(word in query_lower for word in ['calendar', 'schedule', 'meeting', 'appointment']):
                user_context['user_asking_about'] = 'calendar'
                logger.log_reasoning_step("fallback_intent_calendar", {"keywords_matched": ["calendar", "schedule", "meeting", "appointment"]}, user_query, session_id)
            elif any(word in query_lower for word in ['email', 'mail', 'inbox', 'message']):
                user_context['user_asking_about'] = 'email'
                logger.log_reasoning_step("fallback_intent_email", {"keywords_matched": ["email", "mail", "inbox", "message"]}, user_query, session_id)
            elif any(word in query_lower for word in ['document', 'file', 'doc', 'sheet', 'spreadsheet']):
                user_context['user_asking_about'] = 'documents'
                logger.log_reasoning_step("fallback_intent_documents", {"keywords_matched": ["document", "file", "doc", "sheet", "spreadsheet"]}, user_query, session_id)
        
        # Generate intelligent response using Gemini 1.5 Pro
        try:
            logger.log_reasoning_step("ai_response_generation_start", {"context_keys": list(user_context.keys())}, user_query, session_id)
            
            start_time = datetime.utcnow()
            response_text = generate_intelligent_response(
                user_query=user_query,
                image_data=image_data,
                user_context=user_context
            )
            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            logger.log_api_interaction(
                "gemini_1.5_pro",
                "generate_response",
                f"Generated response ({len(response_text)} chars)",
                latency_ms,
                session_id
            )
            
            # Save conversation to memory
            conv_memory.add_message(session_id, "user", user_query)
            conv_memory.add_message(session_id, "assistant", response_text)
            
            # Log complete conversation turn
            logger.log_conversation_turn(user_query, response_text, user_context, session_id)
            
        except Exception as e:
            logger.error(f"Gemini response generation failed: {e}")
            logger.log_reasoning_step("ai_response_generation_failed", {"error": str(e)}, user_query, session_id)
            response_text = f"I understand you said '{user_query}'. I'm processing your request with my advanced AI capabilities, but encountered a technical issue. Let me help you with a thoughtful response instead."
            
            # Still save the conversation even if there was an error
            conv_memory.add_message(session_id, "user", user_query)
            conv_memory.add_message(session_id, "assistant", response_text)
        
        # Generate high-quality audio response
        try:
            logger.info(f"Attempting to synthesize speech for text: '{response_text[:100]}...'")
            response_audio = synthesize_premium_speech(response_text)
            if response_audio and len(response_audio) > 0:
                logger.info(f"Speech synthesis successful, audio size: {len(response_audio)} bytes")
                # For long responses, store in response data
                return response_audio, 200, {
                    'Content-Type': 'audio/mpeg',
                    'X-Response-Text': response_text,  # Full text
                    'X-Response-Length': str(len(response_text)),
                    'X-AI-Model': 'gemini-1.5-pro',
                    'X-User-Transcription': user_query if user_query else ''
                }
            else:
                logger.warning("Speech synthesis returned empty audio")
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
            logger.error(f"Falling back to JSON response for text: '{response_text[:100]}...'", exc_info=True)
        
        # Fallback to JSON response if audio synthesis fails
        # Include API results and intent reasoning if available
        response_data = {
            "status": "success",
            "response": response_text,
            "ai_model": "gemini-1.5-pro",
            "input_type": "audio" if audio_file else "text",
            "message": "Audio synthesis temporarily unavailable, returning text response"
        }
        
        # Add API results and intent reasoning if they exist
        if 'api_results' in user_context:
            response_data['api_results'] = user_context['api_results']
        if 'intent_reasoning' in user_context:
            response_data['intent_reasoning'] = user_context['intent_reasoning']
        
        return jsonify(response_data), 200
            
    except Exception as e:
        logger.error(f"Critical error in orchestrator: {str(e)}", exc_info=True)
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

def get_user_context(auth_code, id_token, user_query=None):
    """Get comprehensive user context from Google Workspace integration"""
    context = {
        "user_authenticated": bool(auth_code and id_token),
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "session": "active"
    }
    
    # Check if user is asking about "today" specifically
    query_lower = user_query.lower() if user_query else ""
    asking_about_today = any(word in query_lower for word in ['today', "today's", 'tonight'])
    
    # Enhanced context with Google Workspace data
    if auth_code:
        try:
            workspace_clients = get_workspace_clients(auth_code)
            credentials = None
            
            # Try to get credentials from the workspace flow
            if workspace_clients and hasattr(workspace_clients, '__iter__'):
                # Extract credentials from one of the clients
                for service_name, service in workspace_clients.items():
                    if hasattr(service, '_http') and hasattr(service._http, 'credentials'):
                        credentials = service._http.credentials
                        break
            
            # Fetch calendar events - check if asking about today
            if asking_about_today and 'calendar' in query_lower:
                context["calendar_events"] = fetch_calendar_events(workspace_clients.get('calendar'), today_only=True)
                context["calendar_query_type"] = "today"
            else:
                context["calendar_events"] = fetch_calendar_events(workspace_clients.get('calendar'))
            
            # Fetch recent emails
            context["recent_emails"] = fetch_recent_emails(workspace_clients.get('gmail'))
            
            # Fetch recent Drive files
            context["recent_files"] = fetch_recent_drive_files(workspace_clients.get('drive'))
            
            # Add current time context
            context["current_time"] = datetime.utcnow().isoformat() + 'Z'
            
            # Enhanced context with additional APIs
            try:
                # Get API key from environment or Secret Manager
                import os
                api_key = os.environ.get('GOOGLE_API_KEY', '')
                
                # Enhance context with location, weather, timezone, contacts, etc.
                context = enhance_user_context(context, credentials=credentials, api_key=api_key)
                
                logger.info("Successfully enriched context with enhanced services")
            except Exception as e:
                logger.warning(f"Failed to enhance context with additional services: {e}")
            
            logger.info("Successfully enriched context with Workspace data")
            
        except Exception as e:
            logger.warning(f"Failed to fetch Workspace context: {e}")
            context["workspace_error"] = "Could not access your Google Workspace data"
    
    return context

# Define function tools for Gemini to call
def define_function_tools():
    """Define the tools/functions available to Gemini"""
    from vertexai.generative_models import FunctionDeclaration, Tool
    
    # Calendar functions
    get_calendar_events_func = FunctionDeclaration(
        name="get_calendar_events",
        description="Get calendar events for a specific time period",
        parameters={
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Number of days ahead to fetch events (default: 7)"
                },
                "today_only": {
                    "type": "boolean", 
                    "description": "Whether to fetch only today's events (default: false)"
                }
            }
        }
    )
    
    # Email functions
    search_emails_func = FunctionDeclaration(
        name="search_emails",
        description="Search for emails in Gmail",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for emails (e.g., 'from:boss', 'subject:report')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)"
                }
            }
        }
    )
    
    # Drive functions
    search_drive_files_func = FunctionDeclaration(
        name="search_drive_files", 
        description="Search for files in Google Drive",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for files (e.g., 'Marketing Strategy', 'type:pdf')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)"
                }
            }
        }
    )
    
    # Create tool with all functions
    function_tool = Tool(
        function_declarations=[
            get_calendar_events_func,
            search_emails_func, 
            search_drive_files_func
        ]
    )
    
    return [function_tool]

def execute_function_call(function_call, workspace_clients, session_id=None):
    """Execute a function call and return the results"""
    function_name = function_call.name
    function_args = dict(function_call.args) if function_call.args else {}
    
    logger.log_function_call(function_name, function_args, "Starting execution", True, session_id)
    
    try:
        if function_name == "get_calendar_events":
            days_ahead = function_args.get("days_ahead", 7)
            today_only = function_args.get("today_only", False)
            events = fetch_calendar_events(
                workspace_clients.get('calendar'), 
                days_ahead=days_ahead, 
                today_only=today_only
            )
            result = {
                "function_name": function_name,
                "result": events,
                "success": True
            }
            logger.log_function_call(function_name, function_args, f"Fetched {len(events)} calendar events", True, session_id)
            return result
            
        elif function_name == "search_emails":
            query = function_args.get("query", "")
            max_results = function_args.get("max_results", 5)
            # For now, use the existing fetch_recent_emails - in production, implement search
            emails = fetch_recent_emails(workspace_clients.get('gmail'), max_results)
            return {
                "function_name": function_name,
                "result": emails,
                "success": True,
                "note": f"Searched recent emails (full search not implemented yet)"
            }
            
        elif function_name == "search_drive_files":
            query = function_args.get("query", "")
            max_results = function_args.get("max_results", 10) 
            # For now, use the existing fetch_recent_drive_files - in production, implement search
            files = fetch_recent_drive_files(workspace_clients.get('drive'))
            return {
                "function_name": function_name,
                "result": files[:max_results],
                "success": True,
                "note": f"Fetched recent files (full search not implemented yet)"
            }
            
        else:
            return {
                "function_name": function_name,
                "result": None,
                "success": False,
                "error": f"Unknown function: {function_name}"
            }
            
    except Exception as e:
        logger.error(f"Function call {function_name} failed: {e}")
        return {
            "function_name": function_name,
            "result": None,
            "success": False,
            "error": str(e)
        }

def generate_intelligent_response(user_query, image_data=None, user_context=None):
    """Generate intelligent, contextual responses using Gemini 1.5 Pro"""
    try:
        # Initialize the most powerful Gemini model
        model = GenerativeModel("gemini-1.5-pro-001")
        
        # Get function tools for API calls
        tools = define_function_tools()
        
        # Create a sophisticated system prompt
        system_prompt = """You are a smart, conversational friend who happens to have access to someone's digital life. Respond EXACTLY like a helpful human friend would.

CRITICAL RULES - FOLLOW THESE EXACTLY:

1. GREETINGS:
   - "Hi"/"Hello" → "Hey! How can I help you today?"
   - "How are you?" → "I'm great! What's going on?"
   - Keep it SHORT and natural

2. CALENDAR QUERIES (Examples from user's list):
   - "What's on my schedule?" → Give exact events with times
   - "Do I have meetings Friday?" → List specific Friday meetings
   - "Schedule project sync Wednesday 10AM" → Confirm scheduling
   - "Find next slot with Jane" → Search and suggest times
   - If no data: "Let me check your calendar... I'm having connection issues. Try again?"

3. EMAIL QUERIES (Examples from user's list):
   - "Any emails from boss?" → Show exact emails from manager
   - "Find Q3 Financials email" → Search and show that specific email
   - "Draft email to sales team" → Start composing immediately
   - "Unread emails?" → List them with senders and subjects
   - If no data: "Checking your emails... Having connection issues. Try again?"

4. DOCUMENT/DRIVE QUERIES (Examples from user's list):
   - "Find Q4 Marketing Strategy" → Locate and show the file
   - "Open Project Phoenix Brief" → Access that specific doc
   - "Recent files?" → List what you worked on
   - "Share Weekly Report with manager" → Do it and confirm
   - If no data: "Searching your Drive... Connection issues. Try again?"

5. WEATHER/LOCATION (Examples from user's list):
   - "Weather in London?" → Give current conditions
   - "Nearest coffee shop?" → Find and give directions
   - "Time zone in Tokyo?" → Show exact time there
   - "Pollen count?" → Give current levels

6. COMPLEX/MULTI-STEP (Examples from user's list):
   - Handle naturally: "Check my calendar and find urgent emails from those people"
   - Process screenshots: "Look at this screenshot and..."
   - Cross-reference: "Find flight email and add to calendar"

7. CONTINUOUS CONVERSATION:
   - After EVERY response, stay engaged:
   - "What else?" or "Need anything else?"
   - Keep listening for next command
   - If user says "stop listening", "stop", "bye", or "goodbye", respond with "Got it! Talk to you later!"

FORBIDDEN PHRASES - NEVER SAY THESE:
- "I'm an AI assistant"
- "I'm designed to help with productivity"  
- "I can assist with various tasks"
- "My capabilities include..."
- "I'm here to help with your digital life"
- ANY explanation of what you are or what you do

ALWAYS:
- Jump straight into helping
- Give specific, actionable information
- Keep responses short and natural
- Sound like a helpful friend, not a robot"""

        # Analyze query type first
        query_lower = user_query.lower() if user_query else ""
        is_greeting = any(greet in query_lower for greet in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you'])
        is_capability_question = any(phrase in query_lower for phrase in ['what can you do', 'what are you', 'who are you', 'your capabilities', 'how do you work'])
        
        # Build the prompt parts
        prompt_parts = [system_prompt]
        
        # Add specific instructions based on query type
        if is_greeting:
            prompt_parts.append("The user just greeted you. Respond warmly and naturally, as a friend would. Ask how they are or what you can help with today.")
        elif is_capability_question:
            prompt_parts.append("The user is asking about what you can do. Instead of listing capabilities, respond conversationally about how you can help them with their calendar, emails, documents, and daily tasks. Give specific examples relevant to their context.")
        # Handle specific query types based on the extensive API list
        elif any(word in query_lower for word in ['calendar', 'schedule', 'meeting', 'appointment', 'event']):
            prompt_parts.append("Calendar query detected. Provide specific event details with times, locations, and attendees. Be conversational but precise.")
        elif any(word in query_lower for word in ['email', 'mail', 'inbox', 'message', 'draft']):
            prompt_parts.append("Email query detected. Show specific emails with senders, subjects, and preview. Handle drafting if requested.")
        elif any(word in query_lower for word in ['document', 'file', 'spreadsheet', 'doc', 'sheet', 'drive', 'folder']):
            prompt_parts.append("Document query detected. Show specific files with names, types, and last modified dates. Handle sharing if requested.")
        elif any(word in query_lower for word in ['weather', 'temperature', 'forecast']):
            prompt_parts.append("Weather query detected. Provide current conditions and forecast. Be specific about location.")
        elif any(word in query_lower for word in ['direction', 'route', 'map', 'location', 'address']):
            prompt_parts.append("Location query detected. Provide specific directions or location information.")
        elif 'screenshot' in query_lower or 'image' in query_lower or 'photo' in query_lower:
            prompt_parts.append("Image analysis requested. Describe what you see and take action based on the content.")
        elif any(word in query_lower for word in ['create', 'new', 'add', 'schedule', 'book']):
            prompt_parts.append("Creation/scheduling action requested. Confirm the action you're taking.")
        elif any(word in query_lower for word in ['find', 'search', 'look for', 'where']):
            prompt_parts.append("Search query detected. Find and present the specific information requested.")
        
        # Add conversation history for context
        if user_context and user_context.get('conversation_history'):
            history = user_context['conversation_history']
            if history:
                conversation_context = "Previous conversation:\n" + "\n".join(history[-10:])  # Last 10 messages
                prompt_parts.append(conversation_context)
                prompt_parts.append("Remember this conversation context when responding. Build upon previous topics naturally.")
        
        # Add user query
        if user_query:
            prompt_parts.append(f"Current user message: {user_query}")
        
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
            
            # Check what the user is asking about and provide relevant context
            user_asking_about = user_context.get('user_asking_about', '')
            
            # Add calendar context if user is asking about it or if available
            if user_asking_about == 'calendar' or user_context.get("calendar_events") is not None:
                if user_context.get("calendar_events"):
                    if user_context.get("calendar_query_type") == "today":
                        calendar_context = "User's calendar events for TODAY:\n"
                    else:
                        calendar_context = "User's upcoming calendar events:\n"
                    
                    for event in user_context["calendar_events"]:
                        # Use formatted time if available
                        time_str = event.get('start_time_formatted', event['start_time'])
                        calendar_context += f"- {event['title']} at {time_str}"
                        if event.get('location'):
                            calendar_context += f" (Location: {event['location']})"
                        calendar_context += "\n"
                    prompt_parts.append(calendar_context)
                    
                    if user_asking_about == 'calendar':
                        if user_context.get("calendar_query_type") == "today":
                            prompt_parts.append("The user is specifically asking about their calendar for TODAY. List all their events for today in a clear, conversational way.")
                        else:
                            prompt_parts.append("The user is specifically asking about their calendar/schedule. Provide a natural, conversational response about their events.")
                elif user_context.get("calendar_events") == []:
                    # Empty list means no events
                    if user_context.get("calendar_query_type") == "today":
                        prompt_parts.append("The user's calendar shows NO EVENTS for today. Let them know their calendar is free/clear for today.")
                    else:
                        prompt_parts.append("The user's calendar shows NO upcoming events. Let them know their calendar is clear.")
                else:
                    prompt_parts.append("Note: Calendar data is not currently available, but the user is asking about their schedule.")
            
            # Add email context if user is asking about it or if available
            if user_asking_about == 'email' or user_context.get("recent_emails"):
                if user_context.get("recent_emails"):
                    email_context = "User's recent emails:\n"
                    for email in user_context["recent_emails"]:
                        email_context += f"- From {email['sender']}: {email['subject']}\n"
                        if email.get('snippet'):
                            email_context += f"  Preview: {email['snippet']}\n"
                    prompt_parts.append(email_context)
                    if user_asking_about == 'email':
                        prompt_parts.append("The user is specifically asking about their emails. Provide a natural, conversational summary of their inbox.")
                else:
                    prompt_parts.append("Note: Email data is not currently available, but the user is asking about their emails.")
            
            # Add Drive files context if user is asking about documents or if available
            if user_asking_about == 'documents' or user_context.get("recent_files"):
                if user_context.get("recent_files"):
                    files_context = "User's recent Drive files:\n"
                    for file in user_context["recent_files"]:
                        files_context += f"- {file['name']} ({file['type']}) - Modified: {file['modified']}\n"
                    prompt_parts.append(files_context)
                    if user_asking_about == 'documents':
                        prompt_parts.append("The user is specifically asking about their documents/files. Provide a natural, conversational response about their recent files.")
                else:
                    prompt_parts.append("Note: Drive/document data is not currently available, but the user is asking about their files.")
            
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
        
        # Generate response with function calling capability
        response = model.generate_content(
            prompt_parts,
            generation_config=generation_config,
            safety_settings=safety_settings,
            tools=tools
        )
        
        # Check if Gemini wants to call a function
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    # Gemini wants to call a function - execute it
                    function_call = part.function_call
                    
                    # Get workspace clients for function execution
                    auth_code = user_context.get('auth_code') if user_context else None
                    workspace_clients = {}
                    if auth_code:
                        try:
                            workspace_clients = get_workspace_clients(auth_code)
                        except Exception as e:
                            logger.error(f"Failed to get workspace clients for function call: {e}")
                    
                    # Execute the function call
                    function_result = execute_function_call(function_call, workspace_clients, session_id)
                    
                    # Send the function result back to Gemini for a final response
                    function_response_parts = prompt_parts.copy()
                    function_response_parts.append(f"Function call result: {json.dumps(function_result, indent=2)}")
                    function_response_parts.append("Based on this data, provide a natural, conversational response to the user.")
                    
                    # Generate final response with the function result
                    final_response = model.generate_content(
                        function_response_parts,
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    )
                    
                    if final_response and final_response.text:
                        return final_response.text.strip()
                    else:
                        return f"I found some information for you, but had trouble formatting it. Here's what I found: {function_result.get('result', 'No results')}"
        
        # Standard response without function calling
        if response and response.text:
            return response.text.strip()
        else:
            return "I'm here to help! Could you tell me more about what you need assistance with?"
            
    except Exception as e:
        logger.error(f"Gemini generation error: {e}")
        # Provide natural fallback responses
        query_lower = user_query.lower() if user_query else ""
        
        if any(phrase in query_lower for phrase in ["stop listening", "stop", "bye", "goodbye", "that's all"]):
            return "Got it! Talk to you later!"
        elif any(greet in query_lower for greet in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return "Hey! What's up? What can I help you with today?"
        elif "how are you" in query_lower:
            return "I'm great, thanks! How about you? What's going on?"
        elif any(word in query_lower for word in ["help", "what can you", "capabilities"]):
            return "I can check your calendar, emails, find your documents - whatever you need! What would you like me to look up?"
        elif "calendar" in query_lower or "schedule" in query_lower:
            return "Let me check your calendar... Hmm, I'm having trouble connecting right now. Can you try again in a sec?"
        elif "email" in query_lower or "mail" in query_lower:
            return "Checking your emails... Having some connection issues. Mind trying again?"
        else:
            return "Sure thing! What specifically would you like to know?"

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