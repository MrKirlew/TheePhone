# main_enhanced.py - Ultimate Conversational AI Backend with Full Integration
import functions_framework
from werkzeug.utils import secure_filename
import os
import tempfile
import json
import logging
from flask import jsonify
import base64
from typing import Dict, Optional, List, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import enhanced AI modules
from conversational_ai import ConversationalAI, enhance_gemini_prompt
from perception_engine import PerceptionEngine, ActionPlanner

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

# Enhanced session management with full AI capabilities
class EnhancedUserSession:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversational_ai = ConversationalAI()
        self.perception_engine = PerceptionEngine()
        self.action_planner = ActionPlanner(self.perception_engine)
        self.session_start = datetime.utcnow()
        self.interaction_count = 0
        
    def process_interaction(self, user_input: str, context: Dict) -> Tuple[str, Dict]:
        """Process a complete interaction with all AI systems"""
        self.interaction_count += 1
        
        # 1. Perceive environment and user state
        env_perception = self.perception_engine.perceive_environment({
            "has_audio": context.get("input_type") == "audio",
            "has_image": context.get("has_image", False)
        })
        
        # 2. Analyze user state
        conversation_history = list(self.conversational_ai.memory.short_term_memory)
        user_state = self.perception_engine.perceive_user_state(user_input, conversation_history)
        
        # 3. Analyze conversation flow
        conversation_flow = self.perception_engine.perceive_conversation_flow(user_input, conversation_history)
        
        # 4. Get behavioral patterns
        behavioral_patterns = self.perception_engine.analyze_behavioral_patterns(conversation_history)
        
        # 5. Get complete perception summary
        perception_summary = self.perception_engine.get_perception_summary()
        
        # 6. Plan actions based on perception
        actions = self.action_planner.plan_actions(user_input, context, perception_summary)
        
        # 7. Execute immediate actions
        action_results = self.action_planner.execute_action_plan(actions, context)
        
        # 8. Generate conversational response with all context
        enhanced_context = {
            **context,
            "perception": perception_summary,
            "planned_actions": actions,
            "action_results": action_results
        }
        
        response, metadata = self.conversational_ai.generate_response(user_input, enhanced_context)
        
        # 9. Enhance metadata with full context
        metadata["perception"] = perception_summary
        metadata["executed_actions"] = action_results
        metadata["session_info"] = {
            "user_id": self.user_id,
            "session_duration": (datetime.utcnow() - self.session_start).total_seconds(),
            "interaction_count": self.interaction_count
        }
        
        return response, metadata

# Global session manager
user_sessions = {}

def get_or_create_enhanced_session(user_id: str) -> EnhancedUserSession:
    """Get or create an enhanced user session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = EnhancedUserSession(user_id)
        
        # Load user history from Firestore if available
        if db:
            try:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    session = user_sessions[user_id]
                    
                    # Restore user profile
                    if 'profile' in user_data:
                        session.conversational_ai.memory.user_profile.update(user_data['profile'])
                        
                    # Restore conversation history
                    if 'conversation_history' in user_data:
                        for interaction in user_data['conversation_history'][-20:]:
                            session.conversational_ai.memory.add_interaction(
                                interaction.get('user_input', ''),
                                interaction.get('ai_response', ''),
                                interaction.get('metadata', {})
                            )
                            
                    # Restore behavioral patterns
                    if 'behavioral_patterns' in user_data:
                        session.perception_engine.behavioral_patterns.update(user_data['behavioral_patterns'])
                        
                    logger.info(f"Restored session for user {user_id}")
                    
            except Exception as e:
                logger.error(f"Failed to load user session: {e}")
    
    return user_sessions[user_id]

def save_enhanced_session(user_id: str, session: EnhancedUserSession):
    """Save enhanced user session to Firestore"""
    if not db:
        return
        
    try:
        # Prepare comprehensive data for storage
        user_data = {
            'profile': session.conversational_ai.memory.user_profile,
            'relationship_context': session.conversational_ai.memory.relationship_context,
            'conversation_history': list(session.conversational_ai.memory.long_term_memory),
            'behavioral_patterns': session.perception_engine.behavioral_patterns,
            'user_state_history': session.perception_engine.user_state["mood_trajectory"],
            'session_stats': {
                'total_interactions': session.interaction_count,
                'last_session_duration': (datetime.utcnow() - session.session_start).total_seconds()
            },
            'last_updated': datetime.utcnow()
        }
        
        # Save to Firestore
        db.collection('users').document(user_id).set(user_data, merge=True)
        logger.info(f"Saved enhanced session for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save user session: {e}")

# Google Workspace integration
WORKSPACE_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

def get_workspace_context(auth_code: str) -> Dict:
    """Get comprehensive workspace context"""
    context = {
        "has_workspace_access": False,
        "calendar_events": [],
        "recent_emails": [],
        "recent_files": []
    }
    
    if not auth_code:
        return context
        
    try:
        # Get workspace clients
        from main_conversational import get_workspace_clients, fetch_calendar_events, fetch_recent_emails, fetch_recent_drive_files
        
        clients = get_workspace_clients(auth_code)
        if clients:
            context["has_workspace_access"] = True
            context["calendar_events"] = fetch_calendar_events(clients.get('calendar'))
            context["recent_emails"] = fetch_recent_emails(clients.get('gmail'))
            context["recent_files"] = fetch_recent_drive_files(clients.get('drive'))
            
    except Exception as e:
        logger.error(f"Failed to get workspace context: {e}")
        
    return context

@functions_framework.http
def ultimate_conversational_agent(request):
    """
    Ultimate conversational AI agent with full memory, perception, reasoning, and personality
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
        
        # Extract user ID from token
        user_id = extract_user_id(id_token)
        
        logger.info(f"Request from user {user_id} - Audio: {audio_file is not None}, Text: {bool(text_command)}, Image: {image_file is not None}")
        
        # Get enhanced session
        session = get_or_create_enhanced_session(user_id)
        
        # Process inputs
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
                
        # Use text command if no audio
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
        
        # Validate input
        if not user_query:
            return jsonify({
                "status": "error",
                "message": "No valid input provided. Please send text, audio, or both."
            }), 400
        
        # Build comprehensive context
        context = {
            "user_authenticated": bool(auth_code and id_token),
            "timestamp": datetime.utcnow().isoformat(),
            "input_type": "audio" if audio_file else "text",
            "has_image": image_data is not None,
            **get_workspace_context(auth_code)
        }
        
        # Process interaction through enhanced session
        initial_response, metadata = session.process_interaction(user_query, context)
        
        # Generate final response with Gemini enhancement
        try:
            final_response = generate_ultimate_response(
                user_query=user_query,
                initial_response=initial_response,
                image_data=image_data,
                context=context,
                metadata=metadata,
                session=session
            )
        except Exception as e:
            logger.error(f"Ultimate response generation failed: {e}")
            final_response = initial_response
        
        # Save session state
        save_enhanced_session(user_id, session)
        
        # Generate high-quality audio response
        try:
            response_audio = synthesize_adaptive_speech(final_response, metadata)
            if response_audio and len(response_audio) > 0:
                # Clean the response text for header safety (remove newlines, limit length)
                header_safe_text = final_response.replace('\n', ' ').replace('\r', ' ')[:500]
                
                return response_audio, 200, {
                    'Content-Type': 'audio/mpeg',
                    'X-Response-Text': header_safe_text,
                    'X-Response-Length': str(len(final_response)),
                    'X-AI-Model': 'gemini-1.5-pro-ultimate',
                    'X-User-Session': user_id,
                    'X-Emotional-State': metadata.get('perception', {}).get('user_state', {}).get('emotional_state', 'neutral'),
                    'X-Interaction-Count': str(session.interaction_count)
                }
        except Exception as e:
            logger.error(f"Speech synthesis failed: {e}")
        
        # Fallback to JSON response
        return jsonify({
            "status": "success",
            "response": final_response,
            "ai_model": "gemini-1.5-pro-ultimate",
            "metadata": {
                "session_id": user_id,
                "interaction_count": session.interaction_count,
                "emotional_state": metadata.get('perception', {}).get('user_state', {}).get('emotional_state', 'neutral'),
                "conversation_depth": session.conversational_ai.memory.user_profile.get('interaction_count', 0)
            },
            "message": "Audio synthesis temporarily unavailable, returning text response"
        }), 200
            
    except Exception as e:
        logger.error(f"Critical error in ultimate agent: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "I encountered an unexpected error. Let me reset and try again."
        }), 500

def extract_user_id(id_token: Optional[str]) -> str:
    """Extract user ID from token or generate default"""
    if id_token:
        try:
            import hashlib
            return hashlib.md5(id_token.encode()).hexdigest()[:16]
        except:
            pass
    return "default_user"

def transcribe_audio_advanced(audio_data: bytes) -> str:
    """Advanced audio transcription"""
    try:
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_data)
        
        configs = [
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.AMR,
                sample_rate_hertz=8000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_confidence=True,
                model="latest_long"
            ),
            speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                language_code="en-US",
                enable_automatic_punctuation=True,
                model="latest_long"
            )
        ]
        
        for config in configs:
            try:
                response = client.recognize(config=config, audio=audio)
                if response.results and response.results[0].alternatives:
                    return response.results[0].alternatives[0].transcript.strip()
            except:
                continue
        
        return "I couldn't catch that clearly. Could you please repeat?"
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return "I'm having trouble hearing you right now."

def generate_ultimate_response(user_query: str, initial_response: str, image_data: Optional[bytes],
                             context: Dict, metadata: Dict, session: EnhancedUserSession) -> str:
    """Generate the ultimate response using all AI capabilities"""
    try:
        model = GenerativeModel("gemini-1.5-pro-001")
        
        # Build comprehensive prompt
        perception = metadata.get('perception', {})
        user_state = perception.get('user_state', {})
        recommendations = perception.get('recommendations', {})
        
        # Check if this is a calendar query
        is_calendar_query = any(word in user_query.lower() for word in ['calendar', 'schedule', 'appointment', 'meeting', 'event'])
        
        prompt = f"""You are a highly capable personal assistant having a natural conversation.

Current Context:
- User emotional state: {user_state.get('emotional_state', 'neutral')}
- Energy level: {user_state.get('energy_level', 'normal')}
- Time of day: {perception.get('environment', {}).get('time_of_day', 'unknown')}
- Previous interactions: {session.conversational_ai.memory.user_profile.get('interaction_count', 0)}

User Profile:
{json.dumps(session.conversational_ai.memory.user_profile, indent=2)}

Calendar Events Available: {len(context.get('calendar_events', [])) > 0}
Calendar Data: {json.dumps(context.get('calendar_events', []), indent=2)}

User Query: "{user_query}"

CRITICAL INSTRUCTIONS:
1. Respond naturally and conversationally, like a helpful friend would
2. NEVER mention being an AI, assistant, or any technical terms
3. If asked about calendar/schedule, provide specific event details from the Calendar Data
4. Keep responses concise and to the point
5. Match the user's tone and energy
6. If no calendar events exist when asked, just say the calendar is clear
7. Be warm but not overly enthusiastic

Generate a natural, helpful response:"""

        # Add image context if available
        prompt_parts = [prompt]
        if image_data:
            try:
                image_part = Part.from_data(data=image_data, mime_type="image/jpeg")
                prompt_parts.append(image_part)
                prompt_parts.append("Also incorporate insights from the image the user shared.")
            except:
                pass
        
        # Configure for natural conversation
        generation_config = GenerationConfig(
            temperature=0.85,
            top_p=0.95,
            top_k=40,
            max_output_tokens=800,
        )
        
        # Generate response
        response = model.generate_content(
            prompt_parts,
            generation_config=generation_config,
            safety_settings=[
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                )
            ]
        )
        
        if response and response.text:
            return response.text.strip()
        else:
            return initial_response
            
    except Exception as e:
        logger.error(f"Ultimate response generation error: {e}")
        return initial_response

def synthesize_adaptive_speech(text: str, metadata: Dict) -> Optional[bytes]:
    """Synthesize speech that adapts to user's emotional state"""
    try:
        client = texttospeech.TextToSpeechClient()
        
        # Adapt voice based on user state
        user_state = metadata.get('perception', {}).get('user_state', {})
        emotional_state = user_state.get('emotional_state', 'neutral')
        
        # Choose voice characteristics based on emotional state
        if emotional_state in ['anxious', 'stressed', 'sad']:
            # Calming voice
            speaking_rate = 0.95
            pitch = -2.0
            voice_name = "en-US-Neural2-F"  # Warm female voice
        elif emotional_state in ['happy', 'excited']:
            # Energetic voice
            speaking_rate = 1.15
            pitch = 1.0
            voice_name = "en-US-Neural2-J"  # Upbeat neutral voice
        else:
            # Balanced voice
            speaking_rate = 1.05
            pitch = 0.0
            voice_name = "en-US-Neural2-J"
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
            volume_gain_db=0.0,
            sample_rate_hertz=24000
        )
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        if response.audio_content:
            logger.info(f"Generated adaptive audio ({len(response.audio_content)} bytes) for {emotional_state} state")
            return response.audio_content
            
    except Exception as e:
        logger.error(f"Adaptive speech synthesis failed: {e}")
        
    return None

# For local testing
if __name__ == "__main__":
    import functions_framework
    app = functions_framework.create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)