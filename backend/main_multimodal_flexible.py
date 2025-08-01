# main_multimodal_flexible.py - Accepts both text and audio input
import functions_framework
from werkzeug.utils import secure_filename
import os
import tempfile
from flask import jsonify
import base64
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Google Cloud libraries with error handling
try:
    from google.cloud import speech
    from google.cloud import texttospeech
    SPEECH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Speech libraries not available: {e}")
    SPEECH_AVAILABLE = False

# Import vision libraries for image processing
try:
    from google.cloud import vision
    VISION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Vision library not available: {e}")
    VISION_AVAILABLE = False

@functions_framework.http
def multimodal_agent_orchestrator(request):
    """
    Flexible multimodal agent that accepts:
    - Audio files (for voice commands)
    - Text input (for typed commands)
    - Images (for visual analysis)
    """
    if request.method != 'POST':
        return 'Method Not Allowed', 405

    try:
        # Get input from various sources
        audio_file = request.files.get('audio_file')
        text_command = request.form.get('text_command') or request.form.get('voice_command')
        image_file = request.files.get('image_file')
        
        # Authentication tokens
        auth_code = request.form.get('auth_code')
        id_token = request.form.get('id_token')
        
        logger.info(f"Request received - Audio: {audio_file is not None}, Text: {bool(text_command)}, Image: {image_file is not None}")
        
        # Determine input type and process accordingly
        transcribed_text = None
        image_description = None
        
        # Process audio if provided
        if audio_file and SPEECH_AVAILABLE:
            logger.info("Processing audio input...")
            temp_audio_path = save_temp_file(audio_file, 'audio')
            try:
                with open(temp_audio_path, 'rb') as f:
                    audio_bytes = f.read()
                transcribed_text = transcribe_audio(audio_bytes)
                logger.info(f"Transcribed: {transcribed_text}")
            finally:
                cleanup_file(temp_audio_path)
                
        # Use text command if no audio or if audio transcription failed
        elif text_command:
            logger.info("Processing text input...")
            transcribed_text = text_command
            
        # If no text input at all
        if not transcribed_text:
            return jsonify({
                "status": "error",
                "message": "No valid input provided. Send either audio_file or text_command."
            }), 400
            
        # Process image if provided
        if image_file and VISION_AVAILABLE:
            logger.info("Processing image input...")
            temp_image_path = save_temp_file(image_file, 'image')
            try:
                image_description = analyze_image(temp_image_path)
                logger.info(f"Image analysis: {image_description}")
            finally:
                cleanup_file(temp_image_path)
        
        # Generate response based on all inputs
        response_text = generate_response(
            text_input=transcribed_text,
            image_description=image_description,
            auth_code=auth_code
        )
        
        # Generate audio response if speech is available
        if SPEECH_AVAILABLE:
            response_audio = synthesize_speech(response_text)
            return response_audio, 200, {'Content-Type': 'audio/mpeg'}
        else:
            # Return text response if speech synthesis not available
            return jsonify({
                "status": "success",
                "text_response": response_text,
                "input_received": transcribed_text,
                "had_image": image_file is not None
            }), 200
            
    except Exception as e:
        logger.error(f"Error in orchestrator: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal Server Error: {str(e)}"
        }), 500

def save_temp_file(file_obj, prefix):
    """Save uploaded file to temp directory"""
    temp_dir = tempfile.gettempdir()
    filename = secure_filename(file_obj.filename)
    temp_path = os.path.join(temp_dir, f"{prefix}_{filename}")
    file_obj.save(temp_path)
    return temp_path

def cleanup_file(filepath):
    """Remove temporary file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.warning(f"Failed to cleanup {filepath}: {e}")

def transcribe_audio(audio_bytes):
    """Transcribes audio bytes using the Speech-to-Text API."""
    try:
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_bytes)
        
        # Try AMR format first (from Android MediaRecorder)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.AMR,
            sample_rate_hertz=8000,
            language_code="en-US",
        )
        
        try:
            response = client.recognize(config=config, audio=audio)
        except Exception as e:
            logger.warning(f"AMR format failed, trying auto-detect: {e}")
            # Try with encoding auto-detection
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                language_code="en-US",
            )
            response = client.recognize(config=config, audio=audio)
        
        if response.results and response.results[0].alternatives:
            return response.results[0].alternatives[0].transcript
        else:
            return "No speech detected in audio"
            
    except Exception as e:
        logger.error(f"Error in transcription: {e}")
        return f"Transcription error: {str(e)}"

def analyze_image(image_path):
    """Analyze image using Vision API"""
    try:
        client = vision.ImageAnnotatorClient()
        
        with open(image_path, 'rb') as image_file:
            content = image_file.read()
            
        image = vision.Image(content=content)
        
        # Perform multiple analyses
        response = client.annotate_image({
            'image': image,
            'features': [
                {'type_': vision.Feature.Type.LABEL_DETECTION, 'max_results': 10},
                {'type_': vision.Feature.Type.TEXT_DETECTION},
                {'type_': vision.Feature.Type.OBJECT_LOCALIZATION, 'max_results': 10},
            ]
        })
        
        descriptions = []
        
        # Process labels
        if response.label_annotations:
            labels = [label.description for label in response.label_annotations[:5]]
            descriptions.append(f"I see: {', '.join(labels)}")
            
        # Process text
        if response.text_annotations:
            text = response.text_annotations[0].description.strip()
            if text:
                descriptions.append(f"Text in image: {text[:100]}...")
                
        # Process objects
        if response.localized_object_annotations:
            objects = [obj.name for obj in response.localized_object_annotations[:3]]
            descriptions.append(f"Objects detected: {', '.join(objects)}")
            
        return ". ".join(descriptions) if descriptions else "Image analyzed but no specific features detected."
        
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return f"Could not analyze image: {str(e)}"

def generate_response(text_input, image_description=None, auth_code=None):
    """Generate an appropriate response based on inputs"""
    # This is where you'd integrate with your AI model
    # For now, we'll create a simple response
    
    response_parts = []
    
    # Acknowledge the text input
    if text_input:
        response_parts.append(f"I heard you say: {text_input}")
    
    # Add image description if available
    if image_description:
        response_parts.append(f"About the image: {image_description}")
    
    # Add a helpful response
    if "hello" in text_input.lower():
        response_parts.append("Hello! How can I help you today?")
    elif "help" in text_input.lower():
        response_parts.append("I can help you with voice commands, text analysis, and image processing. Just ask!")
    elif "weather" in text_input.lower():
        response_parts.append("I'd need to connect to a weather service to give you current conditions.")
    else:
        response_parts.append("I'm processing your request. This is a demo response.")
    
    return " ".join(response_parts)

def synthesize_speech(text_to_speak):
    """Synthesizes speech from text using the Text-to-Speech API."""
    try:
        client = texttospeech.TextToSpeechClient()
        
        # Configure the text input
        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
        
        # Configure voice settings
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
            name="en-US-Neural2-J"  # Using a Neural2 voice for better quality
        )
        
        # Configure audio output
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content
        
    except Exception as e:
        logger.error(f"Error in speech synthesis: {e}")
        # Return a basic audio error message or empty audio
        return b""  # Empty audio bytes

# For local testing
if __name__ == "__main__":
    # Test the function locally
    app = functions_framework.create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)