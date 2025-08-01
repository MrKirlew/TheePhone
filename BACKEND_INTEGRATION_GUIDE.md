# Backend Integration Guide

## Current Issue
The backend Cloud Function (`multimodal_agent_orchestrator`) expects an audio file in the request, but the app is trying to send text commands directly.

## Backend Expectations

The backend at `https://us-central1-twothreeatefi.cloudfunctions.net/multimodal-agent-orchestrator` expects:
- **Method**: POST
- **Required field**: `audio_file` (audio data)
- **Audio format**: AMR encoding, 8000 Hz sample rate
- **Response**: Audio file (MP3 format)

## Solutions

### Option 1: Modify the App to Record Audio (Recommended)
Instead of using speech-to-text on the device, record the actual audio and send it:

```kotlin
private fun startAudioRecording() {
    mediaRecorder = MediaRecorder().apply {
        setAudioSource(MediaRecorder.AudioSource.MIC)
        setOutputFormat(MediaRecorder.OutputFormat.AMR_NB)
        setAudioEncoder(MediaRecorder.AudioEncoder.AMR_NB)
        setAudioSamplingRate(8000)
        setOutputFile(audioFile.absolutePath)
        prepare()
        start()
    }
}
```

### Option 2: Add Text Endpoint to Backend
Create a new endpoint that accepts text input:

```python
@functions_framework.http
def text_agent_endpoint(request):
    """Handle text-based requests"""
    text = request.form.get('text_command')
    # Process text and return response
```

### Option 3: Convert Text to Audio on Device
Use Android's TextToSpeech to create audio from text:

```kotlin
private fun convertTextToAudio(text: String, callback: (File) -> Unit) {
    val tts = TextToSpeech(this) { status ->
        if (status == TextToSpeech.SUCCESS) {
            val audioFile = File(cacheDir, "tts_audio.wav")
            tts.synthesizeToFile(text, null, audioFile, "tts")
            callback(audioFile)
        }
    }
}
```

## Quick Fix for Testing

To test the backend connection, you can:

1. **Use the voice recording feature** - Hold the microphone button to record actual audio
2. **Test with image processing** - Take a photo to test the multimodal functionality
3. **Check backend logs** - Verify requests are reaching your Cloud Function

## Recommended Implementation

1. **For Voice Commands**:
   - Record actual audio using MediaRecorder
   - Send the audio file to backend
   - Backend transcribes and processes
   - Returns audio response

2. **For Text Commands**:
   - Either convert text to speech on device
   - Or create a separate text endpoint
   - Or modify backend to accept both audio and text

3. **For Image Processing**:
   - Current implementation should work
   - Sends image with voice/text description

## Backend Modifications Needed

If you want to support text input, modify your backend:

```python
# Check for audio OR text input
audio_file = request.files.get('audio_file')
text_command = request.form.get('text_command')

if audio_file:
    # Process audio as before
    transcribed_text = transcribe_audio(audio_bytes)
elif text_command:
    # Use text directly
    transcribed_text = text_command
else:
    return jsonify({"error": "No input provided"}), 400
```