# realtime_agent.py - Advanced Real-Time Gemini Live API Integration

import asyncio
import websockets
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
import base64
from datetime import datetime, timedelta
import os
from dataclasses import dataclass, asdict
import aiohttp

# Google Cloud and Gemini imports
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part, Tool, FunctionDeclaration
    from google.cloud import secretmanager
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import google.auth
    SERVICES_AVAILABLE = True
except ImportError as e:
    logging.error(f"Required libraries not available: {e}")
    SERVICES_AVAILABLE = False

# Local imports
from context_cache import ContextCacheManager
from prompt_engineering import (
    PromptPersonalityEngine, PersonalityType, ConversationContext,
    UserPersonalityProfile, ConversationState, get_prompt_engine
)

logger = logging.getLogger(__name__)

@dataclass
class ConversationContext:
    """Manages conversation state and context for the AI agent"""
    user_id: str
    conversation_id: str
    context_cache_token: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = None
    user_workspace_data: Dict[str, Any] = None
    active_functions: List[str] = None
    last_interaction: datetime = None
    
    # Prompt engineering fields
    personality_type: PersonalityType = PersonalityType.PROFESSIONAL
    user_profile: Optional[UserPersonalityProfile] = None
    conversation_state: Optional[ConversationState] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_workspace_data is None:
            self.user_workspace_data = {}
        if self.active_functions is None:
            self.active_functions = []
        if self.last_interaction is None:
            self.last_interaction = datetime.now()
        if self.user_profile is None:
            self.user_profile = UserPersonalityProfile()
        if self.conversation_state is None:
            from prompt_engineering import ConversationContext as PromptConversationContext
            self.conversation_state = ConversationState(
                current_context=PromptConversationContext.PERSONAL
            )

class RealtimeAIAgent:
    """
    Advanced Real-Time AI Agent using Gemini Live API
    
    This class implements the sophisticated architecture described in
    Realtime_Humanlike_AIAgent.txt for natural, continuous dialogue.
    """
    
    def __init__(self, project_id: str = "twothreeatefi"):
        self.project_id = project_id
        self.gemini_live_url = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.StreamGenerateContent"
        self.active_conversations: Dict[str, ConversationContext] = {}
        self.function_registry = {}
        self.setup_complete = False
        
        # Initialize Vertex AI
        if SERVICES_AVAILABLE:
            try:
                vertexai.init(project=project_id, location="us-central1")
                logger.info("Vertex AI initialized for real-time agent")
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI: {e}")
    
    async def setup_agent(self):
        """Initialize the real-time agent with all required components"""
        try:
            # Register Google Workspace function tools
            self._register_workspace_functions()
            
            # Setup context caching system
            await self._initialize_context_cache()
            
            self.setup_complete = True
            logger.info("Real-time AI agent setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup real-time agent: {e}")
            raise
    
    async def _initialize_context_cache(self):
        """Initialize the context caching system for long conversations"""
        try:
            self.context_cache = ContextCacheManager(
                project_id=self.project_id,
                ttl_hours=24,  # Cache valid for 24 hours
                max_cache_size=50000  # 50K tokens max per cache
            )
            
            await self.context_cache.initialize()
            logger.info("Context caching system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize context cache: {e}")
            # Continue without caching rather than failing completely
            self.context_cache = None
    
    def _register_workspace_functions(self):
        """Register all available function tools for Gemini Function Calling"""
        
        # Gmail functions
        self.function_registry["search_gmail"] = {
            "declaration": FunctionDeclaration(
                name="search_gmail",
                description="Searches the user's Gmail for messages matching a query",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query like 'from:boss subject:report' or 'is:unread important'"
                        },
                        "max_results": {
                            "type": "integer", 
                            "description": "Maximum number of messages to return (default: 10)"
                        }
                    },
                    "required": ["query"]
                }
            ),
            "function": self._search_gmail
        }
        
        # Calendar functions
        self.function_registry["get_calendar_events"] = {
            "declaration": FunctionDeclaration(
                name="get_calendar_events",
                description="Retrieves calendar events for a specified time period",
                parameters={
                    "type": "object",
                    "properties": {
                        "time_period": {
                            "type": "string",
                            "description": "Time period: 'today', 'tomorrow', 'this_week', 'next_week'"
                        },
                        "calendar_id": {
                            "type": "string",
                            "description": "Specific calendar ID (default: 'primary')"
                        }
                    },
                    "required": ["time_period"]
                }
            ),
            "function": self._get_calendar_events
        }
        
        # Drive functions
        self.function_registry["search_drive_files"] = {
            "declaration": FunctionDeclaration(
                name="search_drive_files", 
                description="Searches for files in Google Drive",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "File search query like 'name contains \"budget\"' or 'modifiedTime > \"2024-01-01\"'"
                        },
                        "file_type": {
                            "type": "string",
                            "description": "File type filter: 'document', 'spreadsheet', 'presentation', 'pdf', 'image'"
                        }
                    },
                    "required": ["query"]
                }
            ),
            "function": self._search_drive_files
        }
        
        # Weather and location functions
        self.function_registry["get_current_weather"] = {
            "declaration": FunctionDeclaration(
                name="get_current_weather",
                description="Gets current weather information for the user's location or specified location",
                parameters={
                    "type": "object", 
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Location name (optional, defaults to user's current location)"
                        }
                    }
                }
            ),
            "function": self._get_current_weather
        }
        
        logger.info(f"Registered {len(self.function_registry)} function tools")
    
    async def _initialize_context_cache(self):
        """Initialize the context caching system for long conversations"""
        try:
            self.context_cache = ContextCacheManager(
                project_id=self.project_id,
                ttl_hours=24,  # Cache valid for 24 hours
                max_cache_size=50000  # 50K tokens max per cache
            )
            
            await self.context_cache.initialize()
            logger.info("Context caching system initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize context cache: {e}")
            # Continue without caching rather than failing completely
            self.context_cache = None
    
    async def start_realtime_conversation(self, 
                                        user_id: str,
                                        auth_credentials: Credentials,
                                        initial_context: Dict[str, Any] = None) -> ConversationContext:
        """
        Start a new real-time conversation session
        
        Returns a ConversationContext that manages the ongoing dialogue
        """
        conversation_id = f"{user_id}_{datetime.now().isoformat()}"
        
        # Create conversation context
        context = ConversationContext(
            user_id=user_id,
            conversation_id=conversation_id,
            user_workspace_data=initial_context or {}
        )
        
        # Store active conversation
        self.active_conversations[conversation_id] = context
        
        # Initialize with user preferences if available
        await self._load_user_personality_preferences(context)
        
        # Prepare workspace clients for function calling
        context.user_workspace_data['credentials'] = auth_credentials
        context.user_workspace_data['workspace_clients'] = await self._build_workspace_clients(auth_credentials)
        
        logger.info(f"Started real-time conversation {conversation_id} for user {user_id}")
        return context
    
    async def _build_workspace_clients(self, credentials: Credentials) -> Dict[str, Any]:
        """Build Google Workspace API clients for function calling"""
        try:
            # Build API clients
            gmail_service = build('gmail', 'v1', credentials=credentials)
            calendar_service = build('calendar', 'v3', credentials=credentials)
            drive_service = build('drive', 'v3', credentials=credentials)
            people_service = build('people', 'v1', credentials=credentials)
            
            return {
                'gmail': gmail_service,
                'calendar': calendar_service, 
                'drive': drive_service,
                'people': people_service
            }
        except Exception as e:
            logger.error(f"Failed to build workspace clients: {e}")
            return {}
    
    async def process_realtime_audio_stream(self,
                                          conversation_context: ConversationContext,
                                          audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
        """
        Process real-time audio stream using Gemini Live API
        
        This implements the core real-time voice processing pipeline
        described in the architectural document.
        """
        
        if not self.setup_complete:
            await self.setup_agent()
        
        try:
            # Get API key for Gemini Live API
            api_key = await self._get_gemini_api_key()
            
            # Try to load cached context if available
            await self._load_cached_context_if_available(conversation_context)
            
            # Generate sophisticated system instructions using prompt engineering
            system_instruction = self._generate_sophisticated_system_instruction(conversation_context)
            
            # Build function tools for this conversation
            available_tools = [tool_info["declaration"] for tool_info in self.function_registry.values()]
            
            # Connect to Gemini Live API via WebSocket
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with websockets.connect(
                self.gemini_live_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                
                # Send initial configuration
                config_message = {
                    "setup": {
                        "model": "models/gemini-2.0-flash-exp",
                        "system_instruction": system_instruction,
                        "tools": [{"function_declarations": available_tools}] if available_tools else [],
                        "generation_config": {
                            "temperature": 0.8,
                            "top_p": 0.95,
                            "max_output_tokens": 8192,
                            "response_modalities": ["AUDIO"],
                            "speech_config": {
                                "voice_config": {
                                    "prebuilt_voice_config": {
                                        "voice_name": "Aoede"  # Natural, conversational voice
                                    }
                                }
                            }
                        }
                    }
                }
                
                await websocket.send(json.dumps(config_message))
                
                # Start bidirectional stream processing
                async def send_audio():
                    """Send audio chunks to Gemini Live API"""
                    try:
                        async for audio_chunk in audio_stream:
                            if audio_chunk:
                                message = {
                                    "realtimeInput": {
                                        "mediaChunks": [{
                                            "mimeType": "audio/pcm",
                                            "data": base64.b64encode(audio_chunk).decode()
                                        }]
                                    }
                                }
                                await websocket.send(json.dumps(message))
                    except Exception as e:
                        logger.error(f"Error sending audio: {e}")
                
                async def receive_responses():
                    """Receive and process responses from Gemini Live API"""
                    try:
                        async for message in websocket:
                            response = json.loads(message)
                            
                            # Handle different types of responses
                            if "serverContent" in response:
                                server_content = response["serverContent"]
                                
                                # Handle function calls
                                if "functionCall" in server_content:
                                    await self._handle_function_call(
                                        server_content["functionCall"],
                                        conversation_context,
                                        websocket
                                    )
                                
                                # Handle audio output
                                elif "modelTurn" in server_content:
                                    model_turn = server_content["modelTurn"]
                                    if "parts" in model_turn:
                                        for part in model_turn["parts"]:
                                            if "inlineData" in part:
                                                audio_data = base64.b64decode(part["inlineData"]["data"])
                                                yield audio_data
                                
                                # Handle turn completion
                                elif "turnComplete" in server_content:
                                    # Update conversation context
                                    conversation_context.last_interaction = datetime.now()
                                    
                                    # Check if we should cache this conversation context
                                    await self._maybe_cache_conversation_context(conversation_context)
                                    
                    except Exception as e:
                        logger.error(f"Error receiving responses: {e}")
                
                # Run both send and receive tasks concurrently
                await asyncio.gather(
                    send_audio(),
                    receive_responses()
                )
                
        except Exception as e:
            logger.error(f"Error in real-time audio processing: {e}")
            raise
    
    def _generate_sophisticated_system_instruction(self, context: ConversationContext) -> str:
        """
        Generate sophisticated system instructions using advanced prompt engineering
        """
        try:
            # Get the prompt engineering engine
            prompt_engine = get_prompt_engine()
            
            # Update conversation state with current metrics
            context.conversation_state.conversation_length = len(context.conversation_history)
            context.conversation_state.last_topics = self._extract_recent_topics(context.conversation_history)
            
            # Determine current conversation context based on recent activity
            current_context = self._infer_conversation_context(context)
            context.conversation_state.current_context = current_context
            
            # Build workspace context information
            workspace_context = {
                'gmail_available': 'gmail' in context.user_workspace_data.get('workspace_clients', {}),
                'calendar_available': 'calendar' in context.user_workspace_data.get('workspace_clients', {}),
                'drive_available': 'drive' in context.user_workspace_data.get('workspace_clients', {}),
                'weather_available': True,  # Always available
            }
            
            # Get cached summary if available
            cached_summary = context.user_workspace_data.get('cached_summary')
            
            # Generate the sophisticated system prompt
            system_prompt = prompt_engine.generate_system_prompt(
                personality_type=context.personality_type,
                user_profile=context.user_profile,
                conversation_state=context.conversation_state,
                workspace_context=workspace_context,
                cached_summary=cached_summary
            )
            
            # Adapt for time of day
            current_time = datetime.now().time()
            system_prompt = prompt_engine.adapt_prompt_for_time_of_day(system_prompt, current_time)
            
            # Check if we should introduce personality variation for long conversations
            if context.conversation_state.conversation_length > 20:
                varied_personality = prompt_engine.generate_personality_variation(
                    context.personality_type,
                    context.conversation_state.conversation_length
                )
                if varied_personality != context.personality_type:
                    logger.info(f"Introducing personality variation: {varied_personality}")
                    context.personality_type = varied_personality
            
            return system_prompt
            
        except Exception as e:
            logger.error(f"Failed to generate sophisticated system instruction: {e}")
            # Fallback to a simple instruction
            return self._fallback_system_instruction(context)
    
    def _extract_recent_topics(self, conversation_history: List[Dict[str, Any]]) -> List[str]:
        """Extract recent topics from conversation history"""
        topics = []
        
        # Look at recent user messages for topic keywords
        recent_messages = [
            msg for msg in conversation_history[-10:]
            if msg.get('role') == 'user'
        ]
        
        for msg in recent_messages:
            content = msg.get('content', '')
            if isinstance(content, str) and len(content) > 10:
                # Simple topic extraction - look for key phrases
                words = content.lower().split()
                if any(word in ['email', 'emails', 'gmail'] for word in words):
                    topics.append('email')
                if any(word in ['calendar', 'schedule', 'meeting', 'appointment'] for word in words):
                    topics.append('calendar')
                if any(word in ['weather', 'temperature', 'forecast'] for word in words):
                    topics.append('weather')
                if any(word in ['work', 'project', 'deadline', 'task'] for word in words):
                    topics.append('work')
        
        return list(set(topics))  # Remove duplicates
    
    def _infer_conversation_context(self, context: ConversationContext) -> 'ConversationContext':
        """Infer the current conversation context from recent activity"""
        from prompt_engineering import ConversationContext as PromptConversationContext
        
        recent_topics = context.conversation_state.last_topics
        
        # Determine context based on topics and function calls
        if any(topic in ['work', 'project', 'deadline', 'email'] for topic in recent_topics):
            return PromptConversationContext.WORK
        elif any(topic in ['calendar', 'schedule', 'meeting'] for topic in recent_topics):
            return PromptConversationContext.WORK
        elif any(func in ['search_gmail', 'send_email', 'create_calendar_event'] for func in context.active_functions):
            return PromptConversationContext.WORK
        elif any(topic in ['learn', 'explain', 'how'] for topic in recent_topics):
            return PromptConversationContext.LEARNING
        elif any(topic in ['creative', 'idea', 'brainstorm'] for topic in recent_topics):
            return PromptConversationContext.CREATIVE
        else:
            return PromptConversationContext.PERSONAL
    
    def _fallback_system_instruction(self, context: ConversationContext) -> str:
        """Fallback system instruction if sophisticated prompting fails"""
        return """You are an advanced, helpful AI assistant with natural conversational abilities. 
        
You have access to the user's Google Workspace and can help with emails, calendar, documents, and other tasks. 
Speak naturally and conversationally, avoiding robotic language. Be proactive and helpful while respecting user privacy.

Always explain what you're doing when accessing user data and combine information from multiple sources to provide comprehensive, useful responses."""
    
    async def _load_user_personality_preferences(self, context: ConversationContext):
        """Load user's personality preferences for AI interactions"""
        try:
            # In a production system, this would load from user preferences database
            # For now, we'll use some intelligent defaults and inference
            
            # Default personality based on time of day and context
            current_hour = datetime.now().hour
            if 9 <= current_hour <= 17:  # Business hours
                context.personality_type = PersonalityType.PROFESSIONAL
            elif 17 < current_hour <= 21:  # Evening
                context.personality_type = PersonalityType.CASUAL
            else:  # Night/early morning
                context.personality_type = PersonalityType.SUPPORTIVE
            
            # Set user profile defaults
            context.user_profile.preferred_formality = "balanced"
            context.user_profile.preferred_verbosity = "moderate"
            context.user_profile.preferred_response_style = "conversational"
            
            logger.info(f"Initialized personality preferences for user {context.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to load user personality preferences: {e}")
    
    def update_user_personality_preferences(
        self, 
        conversation_id: str,
        personality_type: Optional[PersonalityType] = None,
        user_profile_updates: Optional[Dict[str, Any]] = None
    ):
        """Update user's personality preferences during conversation"""
        try:
            if conversation_id not in self.active_conversations:
                logger.warning(f"No active conversation found: {conversation_id}")
                return False
            
            context = self.active_conversations[conversation_id]
            
            if personality_type:
                context.personality_type = personality_type
                logger.info(f"Updated personality type to {personality_type} for {conversation_id}")
            
            if user_profile_updates:
                for key, value in user_profile_updates.items():
                    if hasattr(context.user_profile, key):
                        setattr(context.user_profile, key, value)
                        logger.info(f"Updated user profile {key} to {value} for {conversation_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update personality preferences: {e}")
            return False
    
    async def _maybe_cache_conversation_context(self, context: ConversationContext):
        """Check if conversation should be cached and cache it if needed"""
        try:
            if not self.context_cache:
                return
            
            # Check if conversation is long enough to warrant caching
            should_cache = await self.context_cache.should_cache_context(
                context.conversation_history
            )
            
            if should_cache:
                # Create cached context
                cached_context = await self.context_cache.create_cached_context(
                    user_id=context.user_id,
                    conversation_id=context.conversation_id,
                    conversation_history=context.conversation_history
                )
                
                if cached_context:
                    # Update context with cache information
                    context.context_cache_token = cached_context.cache_token
                    logger.info(f"Cached conversation context for {context.conversation_id}")
                
        except Exception as e:
            logger.error(f"Failed to cache conversation context: {e}")
    
    async def _load_cached_context_if_available(self, context: ConversationContext) -> bool:
        """Load cached context if available for this conversation"""
        try:
            if not self.context_cache:
                return False
            
            # Generate cache ID based on recent conversation
            if len(context.conversation_history) > 10:
                cache_id = self.context_cache._generate_cache_id(
                    context.user_id, 
                    context.conversation_history
                )
                
                cached_context = await self.context_cache.get_cached_context(cache_id)
                
                if cached_context:
                    # Use cached context to seed conversation
                    context.context_cache_token = cached_context.cache_token
                    
                    # Add cached summary to context
                    context.user_workspace_data['cached_summary'] = cached_context.context_summary
                    
                    logger.info(f"Loaded cached context for conversation {context.conversation_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load cached context: {e}")
            return False
    
    async def _handle_function_call(self,
                                  function_call: Dict[str, Any],
                                  context: ConversationContext,
                                  websocket) -> None:
        """Handle function calls from the Gemini model"""
        function_name = function_call.get("name")
        function_args = function_call.get("args", {})
        
        if function_name not in self.function_registry:
            logger.error(f"Unknown function called: {function_name}")
            return
        
        try:
            # Execute the function
            function_impl = self.function_registry[function_name]["function"]
            result = await function_impl(context, **function_args)
            
            # Send function response back to Gemini
            response_message = {
                "realtimeInput": {
                    "functionResponse": {
                        "name": function_name,
                        "response": result
                    }
                }
            }
            
            await websocket.send(json.dumps(response_message))
            
            logger.info(f"Executed function {function_name} successfully")
            
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            
            # Send error response
            error_response = {
                "realtimeInput": {
                    "functionResponse": {
                        "name": function_name,
                        "response": {"error": str(e)}
                    }
                }
            }
            await websocket.send(json.dumps(error_response))
    
    # Function implementations
    async def _search_gmail(self, context: ConversationContext, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search Gmail using the user's authenticated session"""
        try:
            gmail_service = context.user_workspace_data['workspace_clients']['gmail']
            
            # Execute Gmail search
            results = gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_summaries = []
            
            # Get details for each message
            for msg in messages[:max_results]:
                msg_detail = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata'
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_detail['payload']['headers']}
                
                email_summaries.append({
                    'id': msg['id'],
                    'subject': headers.get('Subject', 'No Subject'),
                    'from': headers.get('From', 'Unknown'),
                    'date': headers.get('Date', 'Unknown'),
                    'snippet': msg_detail.get('snippet', '')
                })
            
            return {
                "status": "success",
                "query": query,
                "total_results": len(messages),
                "emails": email_summaries
            }
            
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _get_calendar_events(self, context: ConversationContext, time_period: str, calendar_id: str = 'primary') -> Dict[str, Any]:
        """Get calendar events for specified time period"""
        try:
            calendar_service = context.user_workspace_data['workspace_clients']['calendar']
            
            # Calculate time range based on period
            now = datetime.now()
            if time_period == 'today':
                time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=1)
            elif time_period == 'tomorrow':
                time_min = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=1)
            elif time_period == 'this_week':
                days_ahead = 6 - now.weekday()
                time_min = now.replace(hour=0, minute=0, second=0, microsecond=0)
                time_max = time_min + timedelta(days=days_ahead)
            elif time_period == 'next_week':
                days_ahead = 6 - now.weekday() + 1
                time_min = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
                time_max = time_min + timedelta(days=7)
            else:
                time_min = now
                time_max = now + timedelta(days=1)
            
            # Query calendar events
            events_result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            event_summaries = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                event_summaries.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No Title'),
                    'start_time': start,
                    'location': event.get('location', ''),
                    'description': event.get('description', '')
                })
            
            return {
                "status": "success",
                "time_period": time_period,
                "events": event_summaries
            }
            
        except Exception as e:
            logger.error(f"Calendar events error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _search_drive_files(self, context: ConversationContext, query: str, file_type: str = None) -> Dict[str, Any]:
        """Search Google Drive files"""
        try:
            drive_service = context.user_workspace_data['workspace_clients']['drive']
            
            # Build search query with file type filter
            search_query = query
            if file_type:
                mime_types = {
                    'document': 'application/vnd.google-apps.document',
                    'spreadsheet': 'application/vnd.google-apps.spreadsheet', 
                    'presentation': 'application/vnd.google-apps.presentation',
                    'pdf': 'application/pdf',
                    'image': 'image/'
                }
                if file_type in mime_types:
                    if file_type == 'image':
                        search_query += f" and mimeType contains '{mime_types[file_type]}'"
                    else:
                        search_query += f" and mimeType='{mime_types[file_type]}'"
            
            # Execute Drive search
            results = drive_service.files().list(
                q=search_query,
                fields="files(id,name,mimeType,modifiedTime,webViewLink,size)",
                pageSize=20
            ).execute()
            
            files = results.get('files', [])
            
            file_summaries = []
            for file in files:
                file_summaries.append({
                    'id': file['id'],
                    'name': file['name'],
                    'type': file['mimeType'],
                    'modified': file.get('modifiedTime', ''),
                    'link': file.get('webViewLink', ''),
                    'size': file.get('size', '')
                })
            
            return {
                "status": "success",
                "query": query,
                "files": file_summaries
            }
            
        except Exception as e:
            logger.error(f"Drive search error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _get_current_weather(self, context: ConversationContext, location: str = None) -> Dict[str, Any]:
        """Get current weather information"""
        try:
            # This would integrate with weather API
            # For now, return structured placeholder
            return {
                "status": "success",
                "location": location or "User's current location",
                "weather": {
                    "temperature": "72°F",
                    "condition": "Partly cloudy",
                    "humidity": "65%",
                    "wind": "8 mph NW"
                }
            }
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _get_gemini_api_key(self) -> str:
        """Get Gemini API key from Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.project_id}/secrets/gemini-api-key/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            # Fallback to environment variable
            return os.environ.get('GEMINI_API_KEY', '')


# Usage Example and Integration Points
class RealtimeConversationManager:
    """Manages multiple real-time conversations and their lifecycle"""
    
    def __init__(self):
        self.agent = RealtimeAIAgent()
        self.active_sessions: Dict[str, ConversationContext] = {}
    
    async def start_session(self, user_id: str, auth_credentials: Credentials) -> str:
        """Start a new conversation session for a user"""
        context = await self.agent.start_realtime_conversation(user_id, auth_credentials)
        session_id = context.conversation_id
        self.active_sessions[session_id] = context
        return session_id
    
    async def process_audio_stream(self, session_id: str, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
        """Process audio stream for an active session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        context = self.active_sessions[session_id]
        async for audio_chunk in self.agent.process_realtime_audio_stream(context, audio_stream):
            yield audio_chunk
    
    def end_session(self, session_id: str):
        """End a conversation session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Ended session {session_id}")