"""
Enhanced Intent Detection Service
Handles intents for all 47 APIs in the KirlewPHone system
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from gemini_service import GeminiService

logger = logging.getLogger(__name__)

class EnhancedIntentDetector:
    """Enhanced service for detecting user intents and required actions for all APIs"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        
        # Define all 47 API categories and their actions
        self.api_categories = {
            'calendar': {
                'actions': [
                    'check_schedule', 'find_meetings', 'list_events', 'check_availability',
                    'upcoming_appointments', 'today_events', 'tomorrow_events', 'weekly_schedule'
                ],
                'description': 'Google Calendar API - Manage calendar events and schedules'
            },
            'email': {
                'actions': [
                    'check_inbox', 'read_emails', 'unread_messages', 'find_emails',
                    'emails_from_sender', 'search_emails', 'recent_emails'
                ],
                'description': 'Gmail API - Access and manage email messages'
            },
            'drive': {
                'actions': [
                    'find_files', 'recent_documents', 'search_documents', 'list_files',
                    'shared_files', 'modified_files'
                ],
                'description': 'Google Drive API - Access and manage files in Drive'
            },
            'docs': {
                'actions': [
                    'read_document', 'create_document', 'edit_document', 'find_document_content'
                ],
                'description': 'Google Docs API - Create and edit Google Docs'
            },
            'sheets': {
                'actions': [
                    'read_sheet', 'create_sheet', 'edit_sheet', 'analyze_data'
                ],
                'description': 'Google Sheets API - Create and edit Google Sheets'
            },
            'speech': {
                'actions': [
                    'transcribe_audio', 'recognize_speech', 'process_voice_commands'
                ],
                'description': 'Cloud Speech-to-Text API - Convert speech to text'
            },
            'texttospeech': {
                'actions': [
                    'synthesize_speech', 'generate_audio', 'create_voice_response'
                ],
                'description': 'Cloud Text-to-Speech API - Convert text to speech'
            },
            'vision': {
                'actions': [
                    'analyze_image', 'detect_objects', 'read_text_in_image', 'describe_scene'
                ],
                'description': 'Cloud Vision API - Analyze images and extract information'
            },
            'weather': {
                'actions': [
                    'get_current_weather', 'get_forecast', 'weather_alerts'
                ],
                'description': 'Weather API - Get weather information and forecasts'
            },
            'geolocation': {
                'actions': [
                    'get_location', 'reverse_geocode', 'find_nearby_places'
                ],
                'description': 'Geolocation API - Determine location from IP or coordinates'
            },
            'cloud_storage': {
                'actions': [
                    'upload_file', 'download_file', 'list_buckets', 'delete_file'
                ],
                'description': 'Cloud Storage API - Store and retrieve files'
            },
            'bigquery': {
                'actions': [
                    'run_query', 'analyze_data', 'get_dataset_info'
                ],
                'description': 'BigQuery API - Analyze large datasets'
            },
            'pubsub': {
                'actions': [
                    'publish_message', 'subscribe_to_topic', 'create_topic'
                ],
                'description': 'Cloud Pub/Sub API - Messaging service for real-time communication'
            },
            'firebase_messaging': {
                'actions': [
                    'send_notification', 'register_device', 'subscribe_to_topic'
                ],
                'description': 'Firebase Cloud Messaging API - Send push notifications'
            },
            'cloud_functions': {
                'actions': [
                    'invoke_function', 'deploy_function', 'list_functions'
                ],
                'description': 'Cloud Functions API - Execute serverless functions'
            },
            'cloud_run': {
                'actions': [
                    'deploy_service', 'invoke_service', 'list_services'
                ],
                'description': 'Cloud Run Admin API - Manage containerized applications'
            },
            'cloud_logging': {
                'actions': [
                    'query_logs', 'write_log', 'export_logs'
                ],
                'description': 'Cloud Logging API - Collect and analyze logs'
            },
            'cloud_monitoring': {
                'actions': [
                    'get_metrics', 'create_alert', 'dashboard_view'
                ],
                'description': 'Cloud Monitoring API - Monitor system performance'
            },
            'secret_manager': {
                'actions': [
                    'get_secret', 'store_secret', 'list_secrets'
                ],
                'description': 'Secret Manager API - Manage sensitive information'
            },
            'artifact_registry': {
                'actions': [
                    'upload_artifact', 'list_artifacts', 'delete_artifact'
                ],
                'description': 'Artifact Registry API - Store and manage artifacts'
            },
            'cloud_build': {
                'actions': [
                    'trigger_build', 'get_build_status', 'list_builds'
                ],
                'description': 'Cloud Build API - Automate building applications'
            },
            'iam': {
                'actions': [
                    'get_permissions', 'set_permissions', 'list_users'
                ],
                'description': 'Identity and Access Management (IAM) API - Manage access control'
            },
            'cloud_sql': {
                'actions': [
                    'query_database', 'create_table', 'backup_database'
                ],
                'description': 'Cloud SQL - Managed database service'
            },
            'cloud_trace': {
                'actions': [
                    'get_traces', 'analyze_performance', 'latency_report'
                ],
                'description': 'Cloud Trace API - Track request latency and performance'
            },
            'cloud_asset': {
                'actions': [
                    'list_assets', 'get_asset_info', 'search_assets'
                ],
                'description': 'Cloud Asset API - Manage cloud resources'
            },
            'cloud_identity': {
                'actions': [
                    'get_user_info', 'manage_groups', 'authenticate_user'
                ],
                'description': 'Cloud Identity API - Manage user identities'
            },
            'cloud_resource_manager': {
                'actions': [
                    'list_projects', 'get_project_info', 'manage_folders'
                ],
                'description': 'Cloud Resource Manager API - Manage Google Cloud resources'
            },
            'contacts': {
                'actions': [
                    'get_contacts', 'add_contact', 'search_contacts'
                ],
                'description': 'Contacts API - Manage personal contacts'
            },
            'people': {
                'actions': [
                    'get_profile', 'update_profile', 'find_person'
                ],
                'description': 'People API - Access personal information'
            },
            'maps': {
                'actions': [
                    'get_directions', 'find_place', 'geocode_address'
                ],
                'description': 'Maps JavaScript API - Access mapping and location services'
            },
            'analytics_hub': {
                'actions': [
                    'share_dataset', 'subscribe_listing', 'list_data_exchanges'
                ],
                'description': 'Analytics Hub API - Share analytics data'
            },
            'dataplex': {
                'actions': [
                    'create_lake', 'discover_data', 'profile_data'
                ],
                'description': 'Cloud Dataplex API - Manage data landscapes'
            },
            'datastore': {
                'actions': [
                    'query_entities', 'save_entity', 'delete_entity'
                ],
                'description': 'Cloud Datastore API - NoSQL database service'
            },
            'chat': {
                'actions': [
                    'send_message', 'create_space', 'list_messages'
                ],
                'description': 'Google Chat API - Communicate via Google Chat'
            },
            'recommender': {
                'actions': [
                    'get_recommendations', 'apply_recommendation', 'list_insights'
                ],
                'description': 'Recommender API - Get optimization recommendations'
            },
            'service_management': {
                'actions': [
                    'list_services', 'enable_service', 'disable_service'
                ],
                'description': 'Service Management API - Manage API services'
            },
            'service_usage': {
                'actions': [
                    'list_apis', 'enable_api', 'disable_api'
                ],
                'description': 'Service Usage API - Manage API usage'
            },
            'time_zone': {
                'actions': [
                    'get_time_zone', 'convert_time_zone', 'list_time_zones'
                ],
                'description': 'Time Zone API - Access time zone information'
            },
            'pollen': {
                'actions': [
                    'get_pollen_data', 'get_forecast', 'get_historical_data'
                ],
                'description': 'Pollen API - Get pollen information'
            },
            'identity_toolkit': {
                'actions': [
                    'authenticate_user', 'create_user', 'reset_password'
                ],
                'description': 'Identity Toolkit API - User authentication'
            },
            'legacy_source_repos': {
                'actions': [
                    'get_repo', 'list_repos', 'commit_changes'
                ],
                'description': 'Legacy Cloud Source Repositories API - Access source code repositories'
            },
            'container_registry': {
                'actions': [
                    'list_images', 'get_image_info', 'delete_image'
                ],
                'description': 'Container Registry API - Store and manage Docker images'
            },
            'dataform': {
                'actions': [
                    'run_workflow', 'get_compilation_result', 'list_repositories'
                ],
                'description': 'Dataform API - Data transformation workflows'
            },
            'drive_activity': {
                'actions': [
                    'get_activity', 'list_activities', 'query_activities'
                ],
                'description': 'Drive Activity API - Track Drive file activities'
            },
            'firebase_installations': {
                'actions': [
                    'register_app', 'get_installation', 'delete_installation'
                ],
                'description': 'Firebase Installations API - Manage Firebase app installations'
            },
            'gemini_assist': {
                'actions': [
                    'get_assistance', 'explain_concept', 'generate_content'
                ],
                'description': 'Gemini Cloud Assist API - AI-powered assistance'
            },
            'generative_language': {
                'actions': [
                    'generate_text', 'embed_content', 'run_model'
                ],
                'description': 'Generative Language API - Access generative AI models'
            },
            'vertex_ai': {
                'actions': [
                    'train_model', 'deploy_model', 'predict'
                ],
                'description': 'Vertex AI API - Machine learning platform'
            }
        }
    
    async def detect_intent_and_actions(self, user_input: str) -> Dict[str, Any]:
        """
        Detect user intent and determine required API actions for all 47 APIs
        
        Returns:
        {
            'needs_api_data': bool,
            'is_greeting': bool,
            'is_casual_conversation': bool,
            'apis': {
                'api_name': ['action1', 'action2'],
                ...
            },
            'parameters': {
                'time_frame': 'today|tomorrow|week|null',
                'search_terms': 'optional search terms',
                'sender': 'optional email sender',
                'file_type': 'optional file type',
                'location': 'optional location',
                'date': 'optional date',
                'topic': 'optional topic',
                'person': 'optional person name'
            },
            'confidence': float,
            'reasoning': str
        }
        """
        
        # First check if it's a greeting or casual conversation
        user_input_lower = user_input.lower()
        greeting_patterns = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'howdy', 'greetings']
        casual_patterns = ['how are you', 'what\'s up', 'how\'s it going', 'thank you', 'thanks', 'bye', 'goodbye', 'see you']
        
        is_greeting = any(pattern in user_input_lower for pattern in greeting_patterns)
        is_casual = any(pattern in user_input_lower for pattern in casual_patterns)
        
        # If it's just a greeting or casual conversation, return early
        if is_greeting or is_casual:
            return {
                'needs_api_data': False,
                'is_greeting': is_greeting,
                'is_casual_conversation': is_casual,
                'apis': {},
                'parameters': {},
                'confidence': 1.0,
                'reasoning': 'Greeting or casual conversation detected'
            }
        
        # Create prompt for intent detection
        prompt = f"""
        Analyze the following user request and determine which APIs and actions are needed from the full set of 47 available APIs.
        
        User request: "{user_input}"
        
        Available APIs and their actions:
        {self._format_api_list()}
        
        Respond in JSON format:
        {{
            "needs_api_data": true/false,
            "is_greeting": false,
            "is_casual_conversation": false,
            "apis": {{
                "api_name": ["action1", "action2"],
                ...
            }},
            "parameters": {{
                "time_frame": "today|tomorrow|week|null",
                "search_terms": "extracted search terms or null",
                "sender": "email sender if specified or null",
                "file_type": "document type if specified or null",
                "location": "location if specified or null",
                "date": "date if specified or null",
                "topic": "topic if specified or null",
                "person": "person name if specified or null"
            }},
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation of why these actions were chosen"
        }}
        
        Examples:
        - "What's on my calendar today?" → calendar: ["today_events"], time_frame: "today"
        - "Check my unread emails" → email: ["unread_messages"]
        - "Find documents from last week" → drive: ["recent_documents"], time_frame: "week"
        - "What's the weather like in New York?" → weather: ["get_current_weather"], location: "New York"
        - "Send a notification to my phone" → firebase_messaging: ["send_notification"]
        - "What's the weather like and do I have any meetings today?" → weather: ["get_current_weather"], calendar: ["today_events"]
        - "Weather forecast and nearby restaurants" → weather: ["get_forecast"], geolocation: ["find_nearby_places"]
        """
        
        try:
            response = await self.gemini_service._process_text_only(prompt, context=None)
            
            # Parse JSON response
            try:
                # Extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                
                intent_data = json.loads(json_str)
                
                # Validate and clean the response
                intent_data = self._validate_intent_response(intent_data)
                
                logger.info(f"Intent detected: {intent_data.get('reasoning', 'No reasoning provided')}")
                return intent_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse intent JSON: {e}")
                return self._fallback_intent_detection(user_input)
                
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            return self._fallback_intent_detection(user_input)
    
    def _format_api_list(self) -> str:
        """Format the API list for the prompt"""
        api_list = ""
        for api_name, api_info in self.api_categories.items():
            api_list += f"{api_name}: {', '.join(api_info['actions'][:3])}...\n"
        return api_list
    
    def _validate_intent_response(self, intent_data: Dict) -> Dict[str, Any]:
        """Validate and clean intent response"""
        # Ensure required fields exist
        if 'needs_api_data' not in intent_data:
            intent_data['needs_api_data'] = False
        
        if 'is_greeting' not in intent_data:
            intent_data['is_greeting'] = False
            
        if 'is_casual_conversation' not in intent_data:
            intent_data['is_casual_conversation'] = False
        
        if 'apis' not in intent_data:
            intent_data['apis'] = {}
        
        if 'parameters' not in intent_data:
            intent_data['parameters'] = {}
        
        if 'confidence' not in intent_data:
            intent_data['confidence'] = 0.5
        
        # Validate APIs against known categories
        validated_apis = {}
        for api_name, actions in intent_data['apis'].items():
            if api_name in self.api_categories:
                # Filter out invalid actions
                valid_actions = [
                    action for action in actions
                    if action in self.api_categories[api_name]['actions']
                ]
                validated_apis[api_name] = valid_actions
        
        intent_data['apis'] = validated_apis
        return intent_data
    
    def _fallback_intent_detection(self, user_input: str) -> Dict[str, Any]:
        """Simple regex-based fallback intent detection"""
        user_input_lower = user_input.lower()
        apis = {}
        parameters = {}
        needs_api_data = False
        
        # Check for each API category
        for api_name, api_info in self.api_categories.items():
            # Check if this API is mentioned in the input
            if self._api_mentioned(user_input_lower, api_name, api_info):
                needs_api_data = True
                # Add relevant actions based on context
                apis[api_name] = self._get_relevant_actions(user_input_lower, api_name)
                
                # Extract parameters
                self._extract_parameters(user_input_lower, parameters)
        
        # If no specific APIs found, try to detect general patterns
        if not apis:
            # Calendar patterns
            if re.search(r'calendar|schedule|meeting|appointment|event', user_input_lower):
                needs_api_data = True
                if 'today' in user_input_lower:
                    apis['calendar'] = ['today_events']
                    parameters['time_frame'] = 'today'
                elif 'tomorrow' in user_input_lower:
                    apis['calendar'] = ['tomorrow_events']
                    parameters['time_frame'] = 'tomorrow'
                else:
                    apis['calendar'] = ['check_schedule']
            
            # Email patterns
            if re.search(r'email|mail|message|inbox', user_input_lower):
                needs_api_data = True
                if 'unread' in user_input_lower:
                    apis['email'] = ['unread_messages']
                else:
                    apis['email'] = ['check_inbox']
            
            # Drive patterns
            if re.search(r'document|file|folder|drive', user_input_lower):
                needs_api_data = True
                if 'recent' in user_input_lower:
                    apis['drive'] = ['recent_documents']
                else:
                    apis['drive'] = ['find_files']
                    
            # Weather patterns
            if re.search(r'weather|temperature|forecast', user_input_lower):
                needs_api_data = True
                apis['weather'] = ['get_current_weather']
                # Extract location if mentioned
                location_match = re.search(r'in ([a-zA-Z\s]+)', user_input_lower)
                if location_match:
                    parameters['location'] = location_match.group(1).strip()
        
        return {
            'needs_api_data': needs_api_data,
            'apis': apis,
            'parameters': parameters,
            'confidence': 0.7 if needs_api_data else 0.3,
            'reasoning': 'Fallback regex-based detection'
        }
    
    def _api_mentioned(self, user_input: str, api_name: str, api_info: Dict) -> bool:
        """Check if an API is mentioned in the user input"""
        # Simple check for API name in input
        if api_name in user_input:
            return True
            
        # Check for keywords in API description
        description = api_info.get('description', '').lower()
        # Extract keywords from description (simple approach)
        keywords = description.split()
        for keyword in keywords:
            # Skip articles and common words
            if len(keyword) > 3 and keyword in user_input:
                return True
                
        return False
    
    def _get_relevant_actions(self, user_input: str, api_name: str) -> List[str]:
        """Get relevant actions for an API based on user input"""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated logic here
        return self.api_categories[api_name]['actions'][:2]  # Return first 2 actions
    
    def _extract_parameters(self, user_input: str, parameters: Dict) -> None:
        """Extract parameters from user input"""
        # Extract time frame
        if 'today' in user_input:
            parameters['time_frame'] = 'today'
        elif 'tomorrow' in user_input:
            parameters['time_frame'] = 'tomorrow'
        elif 'week' in user_input:
            parameters['time_frame'] = 'week'
            
        # Extract location
        location_match = re.search(r'in ([a-zA-Z\s]+)', user_input)
        if location_match:
            parameters['location'] = location_match.group(1).strip()
            
        # Extract date
        date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})', user_input)
        if date_match:
            parameters['date'] = date_match.group(1)
            
        # Extract person
        person_match = re.search(r'(?:from|to|about) ([A-Z][a-z]+)', user_input)
        if person_match:
            parameters['person'] = person_match.group(1)
    
    def get_priority_order(self, apis: Dict[str, List[str]]) -> List[tuple]:
        """Get prioritized list of API actions to execute"""
        priorities = []
        
        # Define priority levels for different APIs
        priority_levels = {
            'calendar': 10,  # Highest priority for time-sensitive info
            'email': 9,      # High priority for communication
            'weather': 8,    # High priority for current info
            'geolocation': 7, # Medium-high priority for context
            'drive': 6,      # Medium priority for files
            'speech': 5,     # Medium priority for voice
            'texttospeech': 4, # Medium priority for responses
            'vision': 3,     # Medium priority for images
            'firebase_messaging': 7, # High priority for notifications
            'cloud_logging': 2, # Low priority for monitoring
            'cloud_monitoring': 2 # Low priority for monitoring
        }
        
        # Add all API actions with their priorities
        for api_name, actions in apis.items():
            priority = priority_levels.get(api_name, 1)  # Default low priority
            for action in actions:
                priorities.append((api_name, action, priority))
        
        # Sort by priority (highest first)
        priorities.sort(key=lambda x: x[2], reverse=True)
        return priorities
