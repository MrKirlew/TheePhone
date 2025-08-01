# main.py - Version with Speech-to-Text
import functions_framework
from werkzeug.utils import secure_filename
import os
import tempfile
from flask import jsonify

# Import Google Cloud libraries with error handling
try:
    from google.cloud import speech
    from google.cloud import texttospeech
    SPEECH_AVAILABLE = True
except ImportError as e:
    print(f"Speech import error: {e}")
    SPEECH_AVAILABLE = False

@functions_framework.http
def multimodal_agent_orchestrator(request):
    """
    HTTP Cloud Function with speech functionality
    """
    if request.method != 'POST':
        return 'Method Not Allowed', 405

    try:
        # Check if we have audio file
        audio_file = request.files.get('audio_file')
        
        if not audio_file:
            return jsonify({
                "status": "error",
                "message": "No audio file provided"
            }), 400

        if not SPEECH_AVAILABLE:
            return jsonify({
                "status": "error", 
                "message": "Speech services not available"
            }), 500

        # Save audio file temporarily
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, secure_filename(audio_file.filename))
        audio_file.save(audio_path)

        try:
            # Transcribe audio
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()
            
            transcribed_text = transcribe_audio(audio_bytes)
            
            # Simple response for now
            response_text = f"I heard you say: {transcribed_text}"
            
            # Synthesize speech response
            response_audio = synthesize_speech(response_text)
            
            # Clean up
            os.remove(audio_path)
            
            # Return audio response
            return response_audio, 200, {'Content-Type': 'audio/mpeg'}
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(audio_path):
                os.remove(audio_path)
            raise e
        
    except Exception as e:
        print(f"Error in orchestrator: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Internal Server Error: {str(e)}"
        }), 500

def transcribe_audio(audio_bytes):
    """Transcribes audio bytes using the Speech-to-Text API."""
    try:
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.AMR,
            sample_rate_hertz=8000,
            language_code="en-US",
        )
        response = client.recognize(config=config, audio=audio)
        
        if response.results and response.results[0].alternatives:
            return response.results[0].alternatives[0].transcript
        else:
            return "No speech detected"
    except Exception as e:
        print(f"Error in transcription: {e}")
        return f"Transcription error: {str(e)}"

def synthesize_speech(text_to_speak, voice_choice="Standard"):
    """Synthesizes speech from text using the Text-to-Speech API."""
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)

        if voice_choice == "WaveNet":
            voice_name = "en-US-Wavenet-D"
        else:
            voice_name = "en-US-Standard-C"

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        return response.audio_content
    except Exception as e:
        print(f"Error in speech synthesis: {e}")
        # Return a simple text response if TTS fails
        return text_to_speak.encode('utf-8')