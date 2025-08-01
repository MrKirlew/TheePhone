"""
Enhanced Multimodal Handler for Cloud Function
Integrates Speech-to-Text, Gemini, and Text-to-Speech
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from google.cloud import speech_v1
from google.cloud import texttospeech
from gemini_service import GeminiService
from google_api_service import GoogleAPIService
from intent_detector import IntentDetector
import json
import re

logger = logging.getLogger(__name__)

class MultimodalHandler:
    """Handles complete multimodal processing pipeline"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.google_api_service = GoogleAPIService()
        self.intent_detector = IntentDetector()
        self.speech_client = speech_v1.SpeechClient()
        self.tts_client = texttospeech.TextToSpeechClient()
        self.conversation_history = []
        
    async def process_audio_and_image(
        self,
        audio_data: Optional[bytes] = None,
        image_data: Optional[bytes] = None,
        text_command: Optional[str] = None,
        auth_code: Optional[str] = None,
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process audio and/or image input through the complete pipeline
        
        Args:
            audio_data: Audio bytes to transcribe
            image_data: Image bytes to analyze
            text_command: Direct text input (alternative to audio)
            user_context: User information and session data
            
        Returns:
            Dict containing response audio, text, and metadata
        """
        try:
            # Step 1: Get text input (transcribe audio or use provided text)
            if audio_data and not text_command:
                text_input = await self._transcribe_audio(audio_data)
                if not text_input:
                    raise ValueError("Could not transcribe audio")
            else:
                text_input = text_command or ""
            
            logger.info(f"Processing input: '{text_input[:100]}...'")
            
            # Step 2: Add to conversation history
            self._add_to_history('user', text_input)
            
            # Step 2.5: Detect intent and fetch Google data if needed
            google_data = None
            if auth_code:
                # Use intent detector for smarter data fetching
                intent_result = await self.intent_detector.detect_intent_and_actions(text_input)
                
                if intent_result['needs_google_data']:
                    logger.info(f"Intent detected: {intent_result['reasoning']}")
                    google_data = await self._fetch_google_data_by_intent(intent_result, auth_code)
                    
                    if google_data:
                        # Augment the input with Google data
                        text_input = self._augment_input_with_google_data(text_input, google_data, intent_result)
            
            # Step 3: Process with Gemini
            gemini_response = await self.gemini_service.process_multimodal_request(
                text_input=text_input,
                image_data=image_data,
                context={
                    **user_context,
                    'conversation_history': self.conversation_history[-10:]  # Last 10 turns
                }
            )
            
            if not gemini_response['success']:
                raise Exception(gemini_response.get('error', 'Gemini processing failed'))
            
            response_text = gemini_response['response']
            
            # Step 4: Add response to history
            self._add_to_history('assistant', response_text)
            
            # Step 5: Generate audio response
            audio_response = await self._generate_audio(response_text)
            
            # Step 6: Extract additional insights
            entities = self.gemini_service.extract_entities(text_input)
            sentiment = self.gemini_service.analyze_sentiment(text_input)
            
            return {
                'success': True,
                'audio_response': audio_response,
                'text_response': response_text,
                'transcribed_input': text_input if audio_data else None,
                'model_used': gemini_response['model_used'],
                'has_image': image_data is not None,
                'entities': entities,
                'sentiment': sentiment,
                'conversation_length': len(self.conversation_history)
            }
            
        except Exception as e:
            logger.error(f"Multimodal processing error: {e}")
            error_text = "I apologize, but I encountered an error processing your request."
            error_audio = await self._generate_audio(error_text)
            
            return {
                'success': False,
                'error': str(e),
                'audio_response': error_audio,
                'text_response': error_text
            }
    
    async def _transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using Google Cloud Speech-to-Text"""
        try:
            # Detect audio format based on header
            encoding = speech_v1.RecognitionConfig.AudioEncoding.AMR
            sample_rate = 8000
            
            if audio_data.startswith(b'RIFF'):  # WAV file
                encoding = speech_v1.RecognitionConfig.AudioEncoding.LINEAR16
                sample_rate = 16000
            elif audio_data.startswith(b'\xFF\xFB') or audio_data.startswith(b'ID3'):  # MP3
                encoding = speech_v1.RecognitionConfig.AudioEncoding.MP3
                sample_rate = 16000
            
            config = speech_v1.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=sample_rate,
                language_code='en-US',
                enable_automatic_punctuation=True,
                model='latest_long',
                use_enhanced=True
            )
            
            audio = speech_v1.RecognitionAudio(content=audio_data)
            response = self.speech_client.recognize(config=config, audio=audio)
            
            transcription = ' '.join(
                result.alternatives[0].transcript 
                for result in response.results
            )
            
            logger.info(f"Transcribed audio: {len(transcription)} chars")
            return transcription.strip()
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
    
    async def _generate_audio(self, text: str) -> bytes:
        """Generate audio using Google Text-to-Speech"""
        try:
            # Configure synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Select voice
            voice = texttospeech.VoiceSelectionParams(
                language_code='en-US',
                name='en-US-Neural2-J',  # High-quality neural voice
                ssml_gender=texttospeech.SsmlVoiceGender.MALE
            )
            
            # Configure audio output
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0,
                volume_gain_db=0.0
            )
            
            # Generate speech
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            logger.info(f"Generated audio: {len(response.audio_content)} bytes")
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            raise
    
    def _add_to_history(self, role: str, content: str):
        """Add to conversation history"""
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': int(asyncio.get_event_loop().time())
        })
        
        # Keep only last 50 turns
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    async def process_follow_up(self, text_input: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process follow-up question with conversation context"""
        try:
            # Use Gemini's contextual response generation
            response_text = self.gemini_service.generate_contextual_response(
                user_input=text_input,
                conversation_history=self.conversation_history
            )
            
            # Add to history
            self._add_to_history('user', text_input)
            self._add_to_history('assistant', response_text)
            
            # Generate audio
            audio_response = await self._generate_audio(response_text)
            
            return {
                'success': True,
                'audio_response': audio_response,
                'text_response': response_text,
                'is_follow_up': True
            }
            
        except Exception as e:
            logger.error(f"Follow-up processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def summarize_conversation(self) -> str:
        """Summarize the current conversation"""
        if not self.conversation_history:
            return "No conversation to summarize."
        
        # Build conversation text
        conversation_text = "\n".join([
            f"{turn['role']}: {turn['content']}"
            for turn in self.conversation_history
        ])
        
        # Use Gemini to summarize
        summary = self.gemini_service.summarize_text(
            conversation_text,
            max_length=500
        )
        
        return summary
    
    async def _fetch_google_data_by_intent(self, intent_result: Dict[str, Any], auth_code: str) -> Optional[Dict[str, Any]]:
        """Fetch Google data based on detected intent"""
        google_data = {}
        
        try:
            actions = intent_result.get('actions', {})
            parameters = intent_result.get('parameters', {})
            
            # Execute calendar actions
            if actions.get('calendar'):
                logger.info(f"Executing calendar actions: {actions['calendar']}")
                
                for action in actions['calendar']:
                    if action == 'today_events':
                        google_data['calendar'] = await self.google_api_service.get_today_events(auth_code)
                    elif action == 'tomorrow_events':
                        from datetime import datetime, timedelta
                        tomorrow = datetime.utcnow() + timedelta(days=1)
                        google_data['calendar'] = await self.google_api_service.get_calendar_events(
                            auth_code,
                            time_min=tomorrow.replace(hour=0, minute=0),
                            time_max=tomorrow.replace(hour=23, minute=59)
                        )
                    elif action in ['check_schedule', 'list_events', 'find_meetings']:
                        # Default to upcoming events
                        google_data['calendar'] = await self.google_api_service.get_calendar_events(auth_code)
                    elif action == 'upcoming_appointments':
                        google_data['calendar'] = await self.google_api_service.get_upcoming_meetings(auth_code)
            
            # Execute email actions
            if actions.get('email'):
                logger.info(f"Executing email actions: {actions['email']}")
                
                for action in actions['email']:
                    if action == 'unread_messages':
                        google_data['emails'] = await self.google_api_service.get_gmail_messages(
                            auth_code, query='is:unread'
                        )
                    elif action == 'emails_from_sender' and parameters.get('sender'):
                        google_data['emails'] = await self.google_api_service.get_gmail_messages(
                            auth_code, query=f'from:{parameters["sender"]}'
                        )
                    elif action == 'search_emails' and parameters.get('search_terms'):
                        google_data['emails'] = await self.google_api_service.get_gmail_messages(
                            auth_code, query=parameters['search_terms']
                        )
                    elif action in ['check_inbox', 'read_emails', 'recent_emails']:
                        google_data['emails'] = await self.google_api_service.get_gmail_messages(auth_code)
            
            # Execute drive actions
            if actions.get('drive'):
                logger.info(f"Executing drive actions: {actions['drive']}")
                
                for action in actions['drive']:
                    if action == 'recent_documents':
                        google_data['files'] = await self.google_api_service.get_recent_documents(auth_code)
                    elif action == 'search_documents' and parameters.get('search_terms'):
                        query = f"name contains '{parameters['search_terms']}'"
                        google_data['files'] = await self.google_api_service.get_drive_files(auth_code, query=query)
                    elif action in ['find_files', 'list_files']:
                        google_data['files'] = await self.google_api_service.get_drive_files(auth_code)
            
            return google_data if google_data else None
            
        except Exception as e:
            logger.error(f"Error fetching Google data by intent: {e}")
            return None
    
    async def _fetch_google_data_if_needed(self, user_input: str, auth_code: str) -> Optional[Dict[str, Any]]:
        """Fetch Google data if user query requires it"""
        google_data = {}
        
        # Detect intent using patterns
        calendar_patterns = [
            r'calendar|schedule|meeting|appointment|event',
            r'what.*today|tomorrow|week',
            r'when is|what time',
            r'busy|free time'
        ]
        
        email_patterns = [
            r'email|mail|message|inbox',
            r'unread|new message',
            r'from.*@|sent by',
            r'check.*email'
        ]
        
        drive_patterns = [
            r'document|file|folder|drive',
            r'spreadsheet|presentation|doc',
            r'recent.*file|modified',
            r'find.*document'
        ]
        
        input_lower = user_input.lower()
        
        try:
            # Check for calendar requests
            if any(re.search(pattern, input_lower) for pattern in calendar_patterns):
                logger.info("Detected calendar request, fetching events...")
                
                # Check for specific time requests
                if 'today' in input_lower:
                    google_data['calendar'] = await self.google_api_service.get_today_events(auth_code)
                elif 'tomorrow' in input_lower:
                    from datetime import datetime, timedelta
                    tomorrow = datetime.utcnow() + timedelta(days=1)
                    google_data['calendar'] = await self.google_api_service.get_calendar_events(
                        auth_code, 
                        time_min=tomorrow.replace(hour=0, minute=0),
                        time_max=tomorrow.replace(hour=23, minute=59)
                    )
                else:
                    google_data['calendar'] = await self.google_api_service.get_calendar_events(auth_code)
            
            # Check for email requests
            if any(re.search(pattern, input_lower) for pattern in email_patterns):
                logger.info("Detected email request, fetching messages...")
                
                # Check for specific queries
                if 'unread' in input_lower:
                    google_data['emails'] = await self.google_api_service.get_gmail_messages(
                        auth_code, query='is:unread'
                    )
                elif re.search(r'from\s+(\S+)', input_lower):
                    match = re.search(r'from\s+(\S+)', input_lower)
                    sender = match.group(1)
                    google_data['emails'] = await self.google_api_service.get_gmail_messages(
                        auth_code, query=f'from:{sender}'
                    )
                else:
                    google_data['emails'] = await self.google_api_service.get_gmail_messages(auth_code)
            
            # Check for drive requests
            if any(re.search(pattern, input_lower) for pattern in drive_patterns):
                logger.info("Detected drive request, fetching files...")
                
                if 'recent' in input_lower or 'modified' in input_lower:
                    google_data['files'] = await self.google_api_service.get_recent_documents(auth_code)
                else:
                    google_data['files'] = await self.google_api_service.get_drive_files(auth_code)
            
            return google_data if google_data else None
            
        except Exception as e:
            logger.error(f"Error fetching Google data: {e}")
            return None
    
    def _augment_input_with_google_data(self, user_input: str, google_data: Dict[str, Any], intent_result: Optional[Dict] = None) -> str:
        """Augment user input with fetched Google data"""
        augmented_input = user_input + "\n\n[GOOGLE DATA CONTEXT]:\n"
        
        # Add intent context if available
        if intent_result:
            augmented_input += f"User Intent: {intent_result.get('reasoning', 'Data retrieval requested')}\n"
            augmented_input += f"Confidence: {intent_result.get('confidence', 0.5):.1f}\n\n"
        
        if 'calendar' in google_data:
            augmented_input += "\n" + self.google_api_service.format_events_for_gemini(google_data['calendar'])
        
        if 'emails' in google_data:
            augmented_input += "\n" + self.google_api_service.format_emails_for_gemini(google_data['emails'])
        
        if 'files' in google_data:
            augmented_input += "\n" + self.google_api_service.format_files_for_gemini(google_data['files'])
        
        augmented_input += "\n\n[END GOOGLE DATA]\n\nBased on the above Google data, please provide a helpful and natural response to the user's request. Be specific and reference the actual data when possible."
        
        return augmented_input