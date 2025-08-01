"""
Intent Detection Service
Uses Gemini to detect user intents for Google API calls
"""

import logging
import json
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from gemini_service import GeminiService

logger = logging.getLogger(__name__)

class IntentDetector:
    """Service for detecting user intents and required actions"""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        
        # Define action categories
        self.action_categories = {
            'calendar': [
                'check_schedule', 'find_meetings', 'list_events', 'check_availability',
                'upcoming_appointments', 'today_events', 'tomorrow_events', 'weekly_schedule'
            ],
            'email': [
                'check_inbox', 'read_emails', 'unread_messages', 'find_emails',
                'emails_from_sender', 'search_emails', 'recent_emails'
            ],
            'drive': [
                'find_files', 'recent_documents', 'search_documents', 'list_files',
                'shared_files', 'modified_files'
            ]
        }
    
    async def detect_intent_and_actions(self, user_input: str) -> Dict[str, Any]:
        """
        Detect user intent and determine required Google API actions
        
        Returns:
        {
            'needs_google_data': bool,
            'actions': {
                'calendar': ['action1', 'action2'],
                'email': ['action1'],
                'drive': []
            },
            'parameters': {
                'time_frame': 'today|tomorrow|week',
                'search_terms': 'optional search terms',
                'sender': 'optional email sender',
                'file_type': 'optional file type'
            },
            'confidence': float
        }
        """
        
        # Create prompt for intent detection
        prompt = f"""
        Analyze the following user request and determine if it requires accessing Google services (Calendar, Gmail, Drive).
        
        User request: "{user_input}"
        
        Available actions:
        Calendar: {', '.join(self.action_categories['calendar'])}
        Email: {', '.join(self.action_categories['email'])}
        Drive: {', '.join(self.action_categories['drive'])}
        
        Respond in JSON format:
        {{
            "needs_google_data": true/false,
            "actions": {{
                "calendar": ["action1", "action2"],
                "email": ["action1"],
                "drive": []
            }},
            "parameters": {{
                "time_frame": "today|tomorrow|week|null",
                "search_terms": "extracted search terms or null",
                "sender": "email sender if specified or null",
                "file_type": "document type if specified or null"
            }},
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation of why these actions were chosen"
        }}
        
        Examples:
        - "What's on my calendar today?" → calendar: ["today_events"], time_frame: "today"
        - "Check my unread emails" → email: ["unread_messages"]
        - "Find documents from last week" → drive: ["recent_documents"], time_frame: "week"
        - "What's the weather like?" → needs_google_data: false (no Google services needed)
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
    
    def _validate_intent_response(self, intent_data: Dict) -> Dict[str, Any]:
        """Validate and clean intent response"""
        # Ensure required fields exist
        if 'needs_google_data' not in intent_data:
            intent_data['needs_google_data'] = False
        
        if 'actions' not in intent_data:
            intent_data['actions'] = {'calendar': [], 'email': [], 'drive': []}
        
        if 'parameters' not in intent_data:
            intent_data['parameters'] = {}
        
        if 'confidence' not in intent_data:
            intent_data['confidence'] = 0.5
        
        # Validate actions against known categories
        for category in ['calendar', 'email', 'drive']:
            if category not in intent_data['actions']:
                intent_data['actions'][category] = []
            else:
                # Filter out invalid actions
                valid_actions = [
                    action for action in intent_data['actions'][category]
                    if action in self.action_categories[category]
                ]
                intent_data['actions'][category] = valid_actions
        
        return intent_data
    
    def _fallback_intent_detection(self, user_input: str) -> Dict[str, Any]:
        """Simple regex-based fallback intent detection"""
        import re
        
        user_input_lower = user_input.lower()
        actions = {'calendar': [], 'email': [], 'drive': []}
        parameters = {}
        needs_google_data = False
        
        # Calendar patterns
        if re.search(r'calendar|schedule|meeting|appointment|event', user_input_lower):
            needs_google_data = True
            if 'today' in user_input_lower:
                actions['calendar'].append('today_events')
                parameters['time_frame'] = 'today'
            elif 'tomorrow' in user_input_lower:
                actions['calendar'].append('tomorrow_events')
                parameters['time_frame'] = 'tomorrow'
            else:
                actions['calendar'].append('check_schedule')
        
        # Email patterns
        if re.search(r'email|mail|message|inbox', user_input_lower):
            needs_google_data = True
            if 'unread' in user_input_lower:
                actions['email'].append('unread_messages')
            else:
                actions['email'].append('check_inbox')
        
        # Drive patterns
        if re.search(r'document|file|folder|drive', user_input_lower):
            needs_google_data = True
            if 'recent' in user_input_lower:
                actions['drive'].append('recent_documents')
            else:
                actions['drive'].append('find_files')
        
        return {
            'needs_google_data': needs_google_data,
            'actions': actions,
            'parameters': parameters,
            'confidence': 0.7 if needs_google_data else 0.3,
            'reasoning': 'Fallback regex-based detection'
        }
    
    def get_action_priority(self, actions: Dict[str, List[str]]) -> List[tuple]:
        """Get prioritized list of actions to execute"""
        priorities = []
        
        # Calendar actions (highest priority for time-sensitive info)
        for action in actions.get('calendar', []):
            priorities.append(('calendar', action, 3))
        
        # Email actions (medium priority)
        for action in actions.get('email', []):
            priorities.append(('email', action, 2))
        
        # Drive actions (lowest priority)
        for action in actions.get('drive', []):
            priorities.append(('drive', action, 1))
        
        # Sort by priority (highest first)
        priorities.sort(key=lambda x: x[2], reverse=True)
        
        return priorities