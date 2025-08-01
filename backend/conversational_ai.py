# conversational_ai.py - Advanced Conversational AI System with Memory and Reasoning
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib
from collections import deque
import re

logger = logging.getLogger(__name__)

class ConversationMemory:
    """Advanced memory system for maintaining context across conversations"""
    
    def __init__(self, max_short_term: int = 10, max_long_term: int = 100):
        self.short_term_memory = deque(maxlen=max_short_term)
        self.long_term_memory = deque(maxlen=max_long_term)
        self.user_profile = {
            "name": None,
            "preferences": {},
            "interests": [],
            "conversation_style": "balanced",
            "interaction_count": 0,
            "first_interaction": None,
            "last_interaction": None,
            "topics_discussed": [],
            "emotional_state": "neutral",
            "location": None,
            "routine_patterns": {}
        }
        self.topic_memory = {}  # Topic -> List of relevant memories
        self.relationship_context = {
            "rapport_level": 0,  # 0-100
            "trust_level": 0,    # 0-100
            "formality": 50,     # 0=very casual, 100=very formal
            "humor_preference": 50,  # 0=serious, 100=humorous
        }
        self.pending_actions = []
        self.completed_actions = []
        
    def add_interaction(self, user_input: str, ai_response: str, metadata: Dict = None):
        """Store interaction in memory with metadata"""
        interaction = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "ai_response": ai_response,
            "metadata": metadata or {},
            "topics": self._extract_topics(user_input),
            "sentiment": self._analyze_sentiment(user_input),
            "interaction_id": hashlib.md5(f"{user_input}{datetime.utcnow()}".encode()).hexdigest()[:8]
        }
        
        # Add to short-term memory
        self.short_term_memory.append(interaction)
        
        # Promote important interactions to long-term memory
        if self._is_important_interaction(interaction):
            self.long_term_memory.append(interaction)
            
        # Update user profile
        self._update_user_profile(interaction)
        
        # Update topic memory
        for topic in interaction["topics"]:
            if topic not in self.topic_memory:
                self.topic_memory[topic] = []
            self.topic_memory[topic].append(interaction)
            
        return interaction
        
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from user input"""
        topics = []
        
        # Keywords that indicate topics
        topic_patterns = {
            "weather": r"\b(weather|temperature|rain|sun|cloud|storm|forecast)\b",
            "work": r"\b(work|job|office|meeting|project|deadline|colleague)\b",
            "personal": r"\b(family|friend|home|personal|life|feeling|emotion)\b",
            "technology": r"\b(computer|phone|app|software|AI|technology|code|program)\b",
            "health": r"\b(health|sick|doctor|medicine|exercise|sleep|tired)\b",
            "food": r"\b(food|eat|hungry|breakfast|lunch|dinner|restaurant|cook)\b",
            "entertainment": r"\b(movie|music|game|book|show|watch|play|read)\b",
            "travel": r"\b(travel|trip|vacation|flight|hotel|visit|tour)\b",
            "calendar": r"\b(calendar|event|schedule|appointment|meeting|time|date)\b",
            "email": r"\b(email|mail|message|inbox|send|reply|forward)\b",
            "files": r"\b(file|document|drive|folder|share|upload|download)\b"
        }
        
        text_lower = text.lower()
        for topic, pattern in topic_patterns.items():
            if re.search(pattern, text_lower):
                topics.append(topic)
                
        return topics
        
    def _analyze_sentiment(self, text: str) -> str:
        """Basic sentiment analysis"""
        positive_words = ["good", "great", "happy", "excellent", "wonderful", "love", "amazing", "perfect", "thank"]
        negative_words = ["bad", "terrible", "hate", "awful", "horrible", "angry", "frustrated", "annoyed", "problem"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
            
    def _is_important_interaction(self, interaction: Dict) -> bool:
        """Determine if interaction should be stored in long-term memory"""
        # Store if it contains personal information
        personal_indicators = ["my name is", "i am", "i live", "i work", "i like", "i hate", "remember"]
        if any(indicator in interaction["user_input"].lower() for indicator in personal_indicators):
            return True
            
        # Store if it's about specific events or appointments
        if any(topic in ["calendar", "email", "work"] for topic in interaction["topics"]):
            return True
            
        # Store if sentiment is strong
        if interaction["sentiment"] in ["positive", "negative"]:
            return True
            
        return False
        
    def _update_user_profile(self, interaction: Dict):
        """Update user profile based on interaction"""
        self.user_profile["interaction_count"] += 1
        self.user_profile["last_interaction"] = interaction["timestamp"]
        
        if not self.user_profile["first_interaction"]:
            self.user_profile["first_interaction"] = interaction["timestamp"]
            
        # Extract name if mentioned
        name_match = re.search(r"my name is (\w+)", interaction["user_input"], re.IGNORECASE)
        if name_match:
            self.user_profile["name"] = name_match.group(1)
            
        # Update topics discussed
        for topic in interaction["topics"]:
            if topic not in self.user_profile["topics_discussed"]:
                self.user_profile["topics_discussed"].append(topic)
                
        # Update emotional state
        self.user_profile["emotional_state"] = interaction["sentiment"]
        
        # Update relationship context
        if interaction["sentiment"] == "positive":
            self.relationship_context["rapport_level"] = min(100, self.relationship_context["rapport_level"] + 2)
            self.relationship_context["trust_level"] = min(100, self.relationship_context["trust_level"] + 1)
        elif interaction["sentiment"] == "negative":
            self.relationship_context["rapport_level"] = max(0, self.relationship_context["rapport_level"] - 1)
            
    def get_relevant_context(self, query: str, max_items: int = 5) -> List[Dict]:
        """Retrieve relevant context for the current query"""
        relevant_memories = []
        
        # Get topics from current query
        current_topics = self._extract_topics(query)
        
        # Search in short-term memory first
        for memory in reversed(list(self.short_term_memory)):
            if any(topic in memory["topics"] for topic in current_topics):
                relevant_memories.append(memory)
                
        # Search in topic memory
        for topic in current_topics:
            if topic in self.topic_memory:
                relevant_memories.extend(self.topic_memory[topic][-3:])
                
        # Remove duplicates and sort by recency
        seen = set()
        unique_memories = []
        for memory in relevant_memories:
            if memory["interaction_id"] not in seen:
                seen.add(memory["interaction_id"])
                unique_memories.append(memory)
                
        return sorted(unique_memories, key=lambda x: x["timestamp"], reverse=True)[:max_items]
        
    def get_conversation_summary(self) -> str:
        """Generate a summary of the conversation history"""
        if not self.short_term_memory:
            return "This is our first conversation."
            
        summary_parts = []
        
        # User info
        if self.user_profile["name"]:
            summary_parts.append(f"User's name is {self.user_profile['name']}")
            
        # Interaction stats
        summary_parts.append(f"We've had {self.user_profile['interaction_count']} interactions")
        
        # Topics discussed
        if self.user_profile["topics_discussed"]:
            summary_parts.append(f"We've discussed: {', '.join(self.user_profile['topics_discussed'][:5])}")
            
        # Relationship context
        if self.relationship_context["rapport_level"] > 50:
            summary_parts.append("We have a good rapport")
        elif self.relationship_context["rapport_level"] < 20:
            summary_parts.append("We're still getting to know each other")
            
        return ". ".join(summary_parts) + "."


class ReasoningEngine:
    """Advanced reasoning and decision-making engine"""
    
    def __init__(self, memory: ConversationMemory):
        self.memory = memory
        self.action_templates = {
            "schedule_reminder": {
                "triggers": ["remind me", "don't forget", "remember to"],
                "required_info": ["what", "when"],
                "action": "create_reminder"
            },
            "search_information": {
                "triggers": ["what is", "tell me about", "explain", "how does"],
                "required_info": ["topic"],
                "action": "search_and_explain"
            },
            "check_calendar": {
                "triggers": ["what's on my calendar", "do i have", "when is my", "schedule"],
                "required_info": [],
                "action": "check_calendar"
            },
            "analyze_emotion": {
                "triggers": ["i feel", "i'm feeling", "i am sad", "i am happy"],
                "required_info": [],
                "action": "provide_emotional_support"
            }
        }
        
    def analyze_intent(self, user_input: str, context: Dict) -> Dict:
        """Analyze user intent and determine appropriate action"""
        intent = {
            "primary_intent": None,
            "confidence": 0.0,
            "required_actions": [],
            "missing_information": [],
            "clarification_needed": False,
            "suggested_response_style": "conversational"
        }
        
        # Check for action triggers
        for action_name, action_info in self.action_templates.items():
            for trigger in action_info["triggers"]:
                if trigger in user_input.lower():
                    intent["primary_intent"] = action_name
                    intent["confidence"] = 0.8
                    intent["required_actions"].append(action_info["action"])
                    break
                    
        # Analyze conversation context
        if not intent["primary_intent"]:
            # Check if it's a greeting
            greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
            if any(greeting in user_input.lower() for greeting in greetings):
                intent["primary_intent"] = "greeting"
                intent["confidence"] = 0.9
                
                # Determine time-appropriate response
                current_hour = datetime.utcnow().hour
                if 5 <= current_hour < 12:
                    intent["suggested_response_style"] = "morning_greeting"
                elif 12 <= current_hour < 17:
                    intent["suggested_response_style"] = "afternoon_greeting"
                else:
                    intent["suggested_response_style"] = "evening_greeting"
                    
            # Check if it's a question
            elif user_input.strip().endswith("?") or any(q in user_input.lower() for q in ["what", "when", "where", "why", "how", "who"]):
                intent["primary_intent"] = "question"
                intent["confidence"] = 0.7
                
        return intent
        
    def generate_action_plan(self, intent: Dict, context: Dict) -> List[Dict]:
        """Generate a plan of actions based on intent"""
        actions = []
        
        if intent["primary_intent"] == "schedule_reminder":
            actions.append({
                "type": "extract_reminder_details",
                "priority": 1,
                "data": {"parse_for": ["time", "task"]}
            })
            actions.append({
                "type": "confirm_reminder",
                "priority": 2,
                "data": {}
            })
            
        elif intent["primary_intent"] == "check_calendar":
            actions.append({
                "type": "fetch_calendar_events",
                "priority": 1,
                "data": {"days_ahead": 7}
            })
            actions.append({
                "type": "summarize_events",
                "priority": 2,
                "data": {}
            })
            
        return actions


class ConversationalAI:
    """Main conversational AI system with personality and advanced capabilities"""
    
    def __init__(self):
        self.memory = ConversationMemory()
        self.reasoning = ReasoningEngine(self.memory)
        self.personality = {
            "traits": ["helpful", "empathetic", "knowledgeable", "friendly", "proactive"],
            "communication_style": "warm and conversational",
            "humor_level": 0.3,  # 0-1 scale
            "formality": 0.4,    # 0-1 scale (0=very casual, 1=very formal)
            "verbosity": 0.6     # 0-1 scale (0=very brief, 1=very detailed)
        }
        
    def generate_response(self, user_input: str, context: Dict = None) -> Tuple[str, Dict]:
        """Generate an intelligent, conversational response"""
        # Analyze intent
        intent = self.reasoning.analyze_intent(user_input, context or {})
        
        # Get relevant memories
        relevant_context = self.memory.get_relevant_context(user_input)
        
        # Generate action plan
        actions = self.reasoning.generate_action_plan(intent, context or {})
        
        # Generate response based on intent and personality
        response = self._craft_response(user_input, intent, relevant_context, context)
        
        # Store interaction
        interaction = self.memory.add_interaction(user_input, response, {
            "intent": intent,
            "actions": actions,
            "context": context
        })
        
        return response, {
            "intent": intent,
            "actions": actions,
            "interaction_id": interaction["interaction_id"],
            "memory_context": relevant_context
        }
        
    def _craft_response(self, user_input: str, intent: Dict, memories: List[Dict], context: Dict) -> str:
        """Craft a personalized, conversational response"""
        
        # Handle greetings with personality
        if intent["primary_intent"] == "greeting":
            return self._generate_greeting_response(user_input, memories, context)
            
        # Handle questions
        elif intent["primary_intent"] == "question":
            return self._generate_question_response(user_input, memories, context)
            
        # Handle calendar requests
        elif intent["primary_intent"] == "check_calendar":
            return self._generate_calendar_response(context)
            
        # Default conversational response
        else:
            return self._generate_conversational_response(user_input, memories, context)
            
    def _generate_greeting_response(self, user_input: str, memories: List[Dict], context: Dict) -> str:
        """Generate a warm, personalized greeting"""
        responses = []
        
        # Get user's name if known
        user_name = self.memory.user_profile.get("name", "")
        name_part = f", {user_name}" if user_name else ""
        
        # Time-based greeting
        current_hour = datetime.utcnow().hour
        if 5 <= current_hour < 12:
            time_greeting = "Good morning"
        elif 12 <= current_hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"
            
        # Check if we've interacted before
        if self.memory.user_profile["interaction_count"] == 0:
            responses.append(f"{time_greeting}{name_part}! I'm so glad to meet you. I'm your AI assistant with advanced capabilities - I can help you with your calendar, emails, answer questions, and even analyze images. I'm designed to be conversational and helpful, learning from our interactions to serve you better. What brings you here today?")
        elif self.memory.user_profile["interaction_count"] < 5:
            responses.append(f"{time_greeting}{name_part}! Great to see you again. How can I help you today?")
        else:
            # More familiar greeting for regular users
            last_interaction = self.memory.user_profile.get("last_interaction")
            if last_interaction:
                last_time = datetime.fromisoformat(last_interaction)
                time_diff = datetime.utcnow() - last_time
                
                if time_diff < timedelta(hours=1):
                    responses.append(f"Back so soon{name_part}! What else can I help you with?")
                elif time_diff < timedelta(days=1):
                    responses.append(f"Hey{name_part}! Good to hear from you again. What's on your mind?")
                elif time_diff < timedelta(days=7):
                    responses.append(f"{time_greeting}{name_part}! It's been a few days. How have you been? What can I do for you today?")
                else:
                    responses.append(f"{time_greeting}{name_part}! It's been a while! I've missed our conversations. How can I assist you today?")
                    
        # Add contextual elements if available
        if context and context.get("calendar_events"):
            upcoming_events = len(context["calendar_events"])
            if upcoming_events > 0:
                responses.append(f" By the way, I see you have {upcoming_events} upcoming events on your calendar.")
                
        return " ".join(responses)
        
    def _generate_question_response(self, user_input: str, memories: List[Dict], context: Dict) -> str:
        """Generate an informative response to questions"""
        # This would integrate with the actual Gemini model for answering questions
        # For now, return a template that shows conversational understanding
        
        # Check if we've discussed this topic before
        if memories:
            recent_memory = memories[0]
            return f"Ah, this relates to what we discussed earlier about {recent_memory['topics'][0] if recent_memory['topics'] else 'our previous conversation'}. Let me help you with that..."
        else:
            return "That's a great question! Let me think about this and provide you with a helpful answer..."
            
    def _generate_calendar_response(self, context: Dict) -> str:
        """Generate response about calendar events"""
        if not context or not context.get("calendar_events"):
            return "Let me check your calendar... It looks like you don't have any upcoming events scheduled. Would you like me to help you add something?"
            
        events = context["calendar_events"]
        if len(events) == 1:
            event = events[0]
            return f"You have one upcoming event: '{event['title']}' scheduled for {event['start_time']}. Would you like me to tell you more about it?"
        else:
            response = f"I found {len(events)} upcoming events on your calendar:\n"
            for i, event in enumerate(events[:3], 1):
                response += f"{i}. {event['title']} - {event['start_time']}\n"
            if len(events) > 3:
                response += f"...and {len(events) - 3} more events. Would you like to see all of them?"
            return response
            
    def _generate_conversational_response(self, user_input: str, memories: List[Dict], context: Dict) -> str:
        """Generate a natural conversational response"""
        # Acknowledge the input
        acknowledgments = [
            "I understand",
            "I see",
            "Got it",
            "Interesting",
            "That makes sense"
        ]
        
        # Build response with personality
        response_parts = []
        
        # Add acknowledgment
        import random
        response_parts.append(random.choice(acknowledgments))
        
        # Reference previous conversations if relevant
        if memories and self.memory.relationship_context["rapport_level"] > 30:
            response_parts.append(f"This reminds me of when we talked about {memories[0]['topics'][0] if memories[0]['topics'] else 'something similar'}")
            
        # Add helpful follow-up
        response_parts.append("Is there something specific you'd like me to help you with regarding this?")
        
        return f"{response_parts[0]}. {' '.join(response_parts[1:])}"


# Integration function for the main backend
def enhance_gemini_prompt(user_query: str, context: Dict, conversational_ai: ConversationalAI) -> str:
    """Enhance the Gemini prompt with conversational memory and personality"""
    
    # Get conversational response and metadata
    response, metadata = conversational_ai.generate_response(user_query, context)
    
    # Build enhanced prompt for Gemini
    enhanced_prompt = f"""You are a highly capable, conversational AI assistant with the following characteristics:

Personality Traits: {', '.join(conversational_ai.personality['traits'])}
Communication Style: {conversational_ai.personality['communication_style']}

User Profile:
{json.dumps(conversational_ai.memory.user_profile, indent=2)}

Relationship Context:
- Rapport Level: {conversational_ai.memory.relationship_context['rapport_level']}/100
- Trust Level: {conversational_ai.memory.relationship_context['trust_level']}/100

Recent Conversation History:
{json.dumps([m for m in list(conversational_ai.memory.short_term_memory)[-5:]], indent=2)}

Current User Input: {user_query}
Detected Intent: {metadata['intent']['primary_intent']}

Instructions:
1. Respond in a warm, conversational manner that matches the personality traits
2. Reference previous conversations when relevant
3. Show that you remember and care about the user
4. Be proactive in offering help
5. Use natural language, avoiding robotic phrases
6. Match the user's emotional tone
7. If greeting, make it personal and time-appropriate

Generate a response that feels like it's from a caring, intelligent friend who happens to be an AI."""

    return enhanced_prompt