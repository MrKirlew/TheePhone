"""
Secure Cloud Function for KirlewAI Multimodal Processing
"""

import os
import json
import logging
import asyncio
import base64
from flask import Flask, request, jsonify
from secure_middleware import (
    require_authentication, 
    validate_multimodal_request, 
    add_security_headers,
    SecurityConfig
)
from gemini_service import GeminiService
from multimodal_handler import MultimodalHandler
from google_api_service import GoogleAPIService
from google.cloud import texttospeech
from google.cloud import speech_v1

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Apply security headers to all responses
app.after_request(add_security_headers)

# Initialize services
gemini_service = None
multimodal_handler = None
google_api_service = None
tts_client = None
speech_client = None

def initialize_services():
    """Initialize AI services"""
    global gemini_service, multimodal_handler, google_api_service, tts_client, speech_client
    
    if not multimodal_handler:
        multimodal_handler = MultimodalHandler()
        logger.info("Multimodal handler initialized")
    
    if not gemini_service:
        gemini_service = GeminiService()
        logger.info("Gemini service initialized")
    
    if not google_api_service:
        google_api_service = GoogleAPIService()
        logger.info("Google API service initialized")
    
    if not tts_client:
        tts_client = texttospeech.TextToSpeechClient()
        logger.info("Text-to-Speech client initialized")
    
    if not speech_client:
        speech_client = speech_v1.SpeechClient()
        logger.info("Speech-to-Text client initialized")

@app.route('/multimodal-agent', methods=['POST'])
@require_authentication
@validate_multimodal_request
def handle_multimodal_request():
    """
    Secure endpoint for multimodal AI requests
    """
    try:
        # Get user information from authentication
        user_info = request.user_info
        user_email = user_info.get('email')
        
        logger.info(f"Processing multimodal request for user: {user_email}")
        
        # Get sanitized voice command
        voice_command = getattr(request, 'sanitized_voice_command', '')
        if not voice_command:
            voice_command = request.form.get('voice_command', '')
        
        # Get other parameters
        session_id = request.form.get('session_id', '')
        auth_code = request.form.get('auth_code', '')
        if not auth_code:
            # Try encrypted version
            auth_code = request.form.get('encrypted_auth_code', '')
        
        # Validate required parameters
        if not voice_command:
            return jsonify({'error': 'Voice command is required'}), 400
        
        # Process image file if present
        image_data = None
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file.filename:
                image_data = file.read()
                logger.info(f"Received image file: {file.filename}, size: {len(image_data)} bytes")
        
        # Log the secure request
        logger.info(f"Secure multimodal request - Session: {session_id}, Command length: {len(voice_command)}, Has image: {image_data is not None}")
        
        # Process audio file if present
        audio_data = None
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            if audio_file.filename:
                audio_data = audio_file.read()
                logger.info(f"Received audio file: {audio_file.filename}, size: {len(audio_data)} bytes")
        
        # Process the multimodal request
        response_data = process_multimodal_ai_request(
            voice_command=voice_command,
            audio_data=audio_data,
            image_data=image_data,
            user_email=user_email,
            session_id=session_id
        )
        
        # Return secure JSON response
        response_json = {
            'audio_content': base64.b64encode(response_data).decode('utf-8'),
            'session_id': session_id,
            'processing_status': 'success'
        }
        return jsonify(response_json)
        
    except Exception as e:
        logger.error(f"Error processing multimodal request: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Request processing failed'
        }), 500

def process_multimodal_ai_request(voice_command: str, audio_data: bytes, image_data: bytes, user_email: str, session_id: str) -> bytes:
    """
    Process the multimodal AI request using enhanced handler
    """
    try:
        # Initialize services
        initialize_services()
        
        # Create user context
        user_context = {
            'user_email': user_email,
            'session_id': session_id,
            'timestamp': int(time.time())
        }
        
        # Process with multimodal handler
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            multimodal_handler.process_audio_and_image(
                audio_data=audio_data,
                image_data=image_data,
                text_command=voice_command if not audio_data else None,
                auth_code=auth_code,
                user_context=user_context
            )
        )
        
        if not result['success']:
            raise Exception(result.get('error', 'Processing failed'))
        
        # Log detailed results
        logger.info(f"Multimodal processing complete - Session: {session_id}")
        logger.info(f"Model: {result.get('model_used')}, Has image: {result.get('has_image')}")
        logger.info(f"Sentiment: {result.get('sentiment', {}).get('sentiment')}, Entities: {len(result.get('entities', {}))} types")
        
        # Return audio response
        return result['audio_response']
        
    except Exception as e:
        logger.error(f"AI processing error: {e}")
        # Return error audio response
        return generate_error_audio_response()

def transcribe_audio_file(audio_data: bytes, encoding: str = 'AMR') -> str:
    """
    Transcribe audio using Google Cloud Speech-to-Text
    """
    try:
        initialize_services()
        
        # Configure recognition
        config = speech_v1.RecognitionConfig(
            encoding=getattr(speech_v1.RecognitionConfig.AudioEncoding, encoding),
            sample_rate_hertz=8000 if encoding == 'AMR' else 16000,
            language_code='en-US',
            enable_automatic_punctuation=True,
            model='latest_long'
        )
        
        audio = speech_v1.RecognitionAudio(content=audio_data)
        
        # Perform transcription
        response = speech_client.recognize(config=config, audio=audio)
        
        # Extract transcribed text
        transcription = ' '.join(
            result.alternatives[0].transcript 
            for result in response.results
        )
        
        logger.info(f"Audio transcribed successfully: {len(transcription)} chars")
        return transcription
        
    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        return ""

def process_voice_command_securely(voice_command: str) -> str:
    """
    Process voice command with additional security checks
    """
    try:
        # Additional input validation
        if len(voice_command) > 1000:
            return "Voice command too long"
        
        # Check for sensitive information (placeholder)
        sensitive_patterns = ['password', 'ssn', 'credit card', 'bank account']
        for pattern in sensitive_patterns:
            if pattern.lower() in voice_command.lower():
                logger.warning(f"Sensitive information detected in voice command")
                return "Sensitive information detected and removed"
        
        # Placeholder for actual voice processing
        analysis = f"Voice command processed securely: '{voice_command}'"
        logger.info("Voice command processed securely")
        return analysis
        
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        return "Voice processing failed"

def generate_audio_response_with_tts(response_text: str) -> bytes:
    """
    Generate audio response using Google Text-to-Speech
    """
    try:
        initialize_services()
        
        # Set up synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=response_text)
        
        # Build the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code='en-US',
            name='en-US-Neural2-J',  # High-quality neural voice
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )
        
        # Select the audio format
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        # Perform the text-to-speech request
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        logger.info(f"Audio response generated: {len(response.audio_content)} bytes")
        return response.audio_content
        
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        return generate_error_audio_response()

def generate_error_audio_response() -> bytes:
    """Generate error audio response"""
    try:
        error_text = "I apologize, but I encountered an error processing your request. Please try again."
        return generate_audio_response_with_tts(error_text)
    except:
        # Fallback to basic error response
        return b"ERROR_AUDIO_RESPONSE"

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': int(time.time()),
        'version': '1.0.0'
    })

@app.route('/auth/callback', methods=['GET', 'POST'])
def auth_callback():
    """OAuth callback endpoint"""
    return jsonify({
        'message': 'OAuth callback received',
        'timestamp': int(time.time())
    })

# Cloud Function entry point
def multimodal_agent_orchestrator(request):
    """
    Cloud Function entry point for multimodal agent
    """
    with app.request_context(environ_base=request.environ):
        try:
            response = app.full_dispatch_request()
            return response
        except Exception as e:
            logger.error(f"Cloud Function error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

# Add new endpoint for audio transcription
@app.route('/transcribe', methods=['POST'])
@require_authentication
def transcribe_audio():
    """Transcribe audio file"""
    try:
        if 'audio_file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio_file']
        audio_data = audio_file.read()
        
        # Transcribe the audio
        transcription = transcribe_audio_file(audio_data)
        
        return jsonify({
            'success': True,
            'transcription': transcription
        })
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Add endpoint for text processing with Gemini
@app.route('/process-text', methods=['POST'])
@require_authentication
def process_text():
    """Process text with Gemini"""
    try:
        data = request.get_json()
        text_input = data.get('text', '')
        
        if not text_input:
            return jsonify({'error': 'No text provided'}), 400
        
        # Initialize services
        initialize_services()
        
        # Get user info
        user_info = request.user_info
        context = {
            'user_email': user_info.get('email'),
            'session_id': data.get('session_id', '')
        }
        
        # Process with Gemini
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        response = loop.run_until_complete(
            gemini_service.process_multimodal_request(
                text_input=text_input,
                context=context
            )
        )
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Text processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # For local development
    import time
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)