# grpc_server.py - gRPC Server Implementation for Real-Time AI Agent
# Implements the architecture specified in Realtime_Humanlike_AIAgent.txt

import asyncio
import grpc
import logging
import os
from concurrent import futures
from typing import AsyncIterator, Optional
import json
from datetime import datetime

# Generated gRPC code (would be generated from conversation.proto)
# import conversation_pb2
# import conversation_pb2_grpc

# Local imports
from realtime_agent import RealtimeConversationManager, ConversationContext
from enhanced_services import EnhancedGoogleServices

logger = logging.getLogger(__name__)

class ConversationalAgentService:
    """
    gRPC service implementation for the real-time conversational agent
    
    This implements the bidirectional streaming architecture described
    in the Realtime_Humanlike_AIAgent.txt document
    """
    
    def __init__(self):
        self.conversation_manager = RealtimeConversationManager()
        self.enhanced_services = EnhancedGoogleServices()
        self.active_streams = {}
        
    async def Converse(self, request_iterator, context):
        """
        Bidirectional streaming RPC for real-time conversation
        
        This is the core method that handles the persistent audio stream
        between the Android client and the Gemini Live API
        """
        session_id = None
        audio_stream_queue = asyncio.Queue()
        
        try:
            # Process incoming requests
            async def process_requests():
                nonlocal session_id
                
                async for request in request_iterator:
                    if request.HasField('session_setup'):
                        # Handle session initialization
                        setup = request.session_setup
                        session_id = await self._initialize_session(setup)
                        
                        # Send session status
                        yield self._create_session_status_response(session_id, "SESSION_ACTIVE")
                        
                    elif request.HasField('audio_chunk'):
                        # Queue audio chunk for processing
                        await audio_stream_queue.put(request.audio_chunk.data)
                        
                    elif request.HasField('text_input'):
                        # Handle text input (hybrid mode)
                        text_response = await self._process_text_input(
                            session_id, 
                            request.text_input.text
                        )
                        yield text_response
                        
                    elif request.HasField('interruption'):
                        # Handle user interruption
                        await self._handle_interruption(session_id, request.interruption)
                        
                    elif request.HasField('context_update'):
                        # Handle context updates
                        await self._update_context(session_id, request.context_update)
            
            # Process audio stream through real-time agent
            async def process_audio_stream():
                if session_id:
                    async def audio_generator():
                        while True:
                            try:
                                audio_chunk = await asyncio.wait_for(
                                    audio_stream_queue.get(), 
                                    timeout=1.0
                                )
                                yield audio_chunk
                            except asyncio.TimeoutError:
                                # Check if stream is still active
                                if session_id not in self.conversation_manager.active_sessions:
                                    break
                                continue
                    
                    # Process through real-time agent
                    async for audio_response in self.conversation_manager.process_audio_stream(
                        session_id, 
                        audio_generator()
                    ):
                        # Create response message
                        response = self._create_audio_response(audio_response)
                        yield response
            
            # Run both processing tasks concurrently
            async for response in asyncio.gather(
                process_requests(),
                process_audio_stream()
            ):
                yield response
                
        except Exception as e:
            logger.error(f"Error in Converse RPC: {e}")
            # Send error response
            error_response = self._create_error_response(
                "UNKNOWN_ERROR", 
                str(e)
            )
            yield error_response
            
        finally:
            # Clean up session
            if session_id:
                self.conversation_manager.end_session(session_id)
    
    async def StartSession(self, request, context):
        """Start a new conversation session"""
        try:
            # Validate authentication
            auth_credentials = await self._validate_auth_token(request.auth_token)
            if not auth_credentials:
                return self._create_session_response(
                    "", 
                    "SESSION_ERROR", 
                    "Authentication failed"
                )
            
            # Start session
            session_id = await self.conversation_manager.start_session(
                request.user_id, 
                auth_credentials
            )
            
            # Get available functions
            available_functions = list(self.conversation_manager.agent.function_registry.keys())
            
            return self._create_session_response(
                session_id,
                "SESSION_ACTIVE", 
                "Session started successfully",
                available_functions
            )
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return self._create_session_response(
                "",
                "SESSION_ERROR",
                str(e)
            )
    
    async def EndSession(self, request, context):
        """End a conversation session"""
        try:
            self.conversation_manager.end_session(request.session_id)
            return {"success": True, "message": "Session ended successfully"}
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return {"success": False, "message": str(e)}
    
    async def ProcessTextCommand(self, request, context):
        """Process a text command (for testing/debugging)"""
        try:
            # This would process text through the same pipeline
            # but return text response instead of audio
            session_context = self.conversation_manager.active_sessions.get(request.session_id)
            if not session_context:
                return {
                    "response_text": "Session not found",
                    "function_calls": [],
                    "audio_url": ""
                }
            
            # Process command through enhanced services
            enhanced_context = self.enhanced_services.build_enhanced_context()
            
            # Generate response (this would integrate with Gemini for text)
            response_text = f"Processed command: {request.command}"
            
            return {
                "response_text": response_text,
                "function_calls": [],
                "audio_url": ""
            }
            
        except Exception as e:
            logger.error(f"Error processing text command: {e}")
            return {
                "response_text": f"Error: {str(e)}",
                "function_calls": [],
                "audio_url": ""
            }
    
    # Helper methods
    async def _initialize_session(self, setup):
        """Initialize a new conversation session"""
        # Validate auth token
        auth_credentials = await self._validate_auth_token(setup.auth_token)
        if not auth_credentials:
            raise Exception("Authentication failed")
        
        # Start session with conversation manager
        session_id = await self.conversation_manager.start_session(
            setup.user_id,
            auth_credentials
        )
        
        # Configure session preferences
        session_context = self.conversation_manager.active_sessions[session_id]
        self._apply_user_preferences(session_context, setup.preferences)
        
        return session_id
    
    async def _validate_auth_token(self, auth_token):
        """Validate authentication token and return credentials"""
        try:
            # This would validate the JWT token and extract credentials
            # For now, return a placeholder
            # In production, this would:
            # 1. Validate JWT signature
            # 2. Check token expiration
            # 3. Extract Google OAuth credentials
            # 4. Return valid Credentials object
            
            # Placeholder implementation
            if auth_token and len(auth_token) > 10:
                # Return mock credentials for now
                return "valid_credentials"
            return None
            
        except Exception as e:
            logger.error(f"Auth validation error: {e}")
            return None
    
    def _apply_user_preferences(self, session_context, preferences):
        """Apply user preferences to session context"""
        if preferences:
            # Store preferences in session context
            session_context.user_workspace_data['preferences'] = {
                'voice_preference': preferences.voice_preference,
                'speech_rate': preferences.speech_rate,
                'enable_interruptions': preferences.enable_interruptions,
                'enable_proactive_suggestions': preferences.enable_proactive_suggestions,
                'language_code': preferences.language_code
            }
    
    async def _process_text_input(self, session_id, text):
        """Process text input in hybrid mode"""
        # This would process text through the conversation pipeline
        # and return appropriate response
        return self._create_transcription_response(
            text, 
            1.0, 
            True, 
            datetime.now().timestamp() * 1000
        )
    
    async def _handle_interruption(self, session_id, interruption):
        """Handle user interruption signal"""
        logger.info(f"Handling interruption for session {session_id}: {interruption.reason}")
        # This would signal the audio processing pipeline to stop current output
        # and prepare for new input
    
    async def _update_context(self, session_id, context_update):
        """Update session context with new information"""
        session_context = self.conversation_manager.active_sessions.get(session_id)
        if session_context:
            if context_update.HasField('location'):
                location = context_update.location
                session_context.user_workspace_data['current_location'] = {
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'address': location.address
                }
            
            # Handle other context updates...
    
    # Response creation helpers
    def _create_audio_response(self, audio_data):
        """Create audio response message"""
        return {
            "audio_chunk": {
                "data": audio_data,
                "timestamp_ms": int(datetime.now().timestamp() * 1000),
                "is_final": False
            }
        }
    
    def _create_transcription_response(self, text, confidence, is_final, timestamp_ms):
        """Create transcription response message"""
        return {
            "transcription": {
                "text": text,
                "confidence": confidence,
                "is_final": is_final,
                "timestamp_ms": int(timestamp_ms)
            }
        }
    
    def _create_session_status_response(self, session_id, state, message=""):
        """Create session status response"""
        return {
            "session_status": {
                "session_id": session_id,
                "state": state,
                "last_activity_ms": int(datetime.now().timestamp() * 1000),
                "status_message": message
            }
        }
    
    def _create_session_response(self, session_id, state, message="", available_functions=None):
        """Create session response"""
        return {
            "session_id": session_id,
            "status": {
                "session_id": session_id,
                "state": state,
                "last_activity_ms": int(datetime.now().timestamp() * 1000),
                "status_message": message
            },
            "available_functions": available_functions or []
        }
    
    def _create_error_response(self, error_code, message, details=""):
        """Create error response message"""
        return {
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
                "timestamp_ms": int(datetime.now().timestamp() * 1000)
            }
        }


async def serve():
    """Start the gRPC server"""
    
    # Create server
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add service
    conversational_agent_service = ConversationalAgentService()
    # conversation_pb2_grpc.add_ConversationalAgentServicer_to_server(
    #     conversational_agent_service, 
    #     server
    # )
    
    # Configure server to listen on Cloud Run port
    port = os.environ.get('PORT', '8080')
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    # Start server
    logger.info(f"Starting gRPC server on {listen_addr}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server")
        await server.stop(5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())