# prompt_engineering.py - Sophisticated Prompt Engineering System

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, time
from dataclasses import dataclass, asdict
from enum import Enum
import random

logger = logging.getLogger(__name__)

class PersonalityType(Enum):
    """Different AI personality types for varied interactions"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENTHUSIASTIC = "enthusiastic"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    SUPPORTIVE = "supportive"

class ConversationContext(Enum):
    """Different conversation contexts that affect prompt style"""
    WORK = "work"
    PERSONAL = "personal"
    LEARNING = "learning"
    CREATIVE = "creative"
    PROBLEM_SOLVING = "problem_solving"
    SOCIAL = "social"

@dataclass
class UserPersonalityProfile:
    """User's personality preferences for AI interactions"""
    preferred_formality: str = "balanced"  # formal, casual, balanced
    preferred_verbosity: str = "moderate"  # brief, moderate, detailed
    preferred_response_style: str = "balanced"  # direct, conversational, analytical
    communication_preferences: List[str] = None
    expertise_areas: List[str] = None
    learning_style: str = "visual"  # visual, auditory, kinesthetic, reading
    
    def __post_init__(self):
        if self.communication_preferences is None:
            self.communication_preferences = []
        if self.expertise_areas is None:
            self.expertise_areas = []

@dataclass
class ConversationState:
    """Current conversation state that influences prompting"""
    current_context: ConversationContext
    user_mood: Optional[str] = None
    conversation_length: int = 0
    last_topics: List[str] = None
    current_tasks: List[str] = None
    user_stress_level: str = "normal"  # low, normal, high
    time_pressure: bool = False
    
    def __post_init__(self):
        if self.last_topics is None:
            self.last_topics = []
        if self.current_tasks is None:
            self.current_tasks = []

class PromptPersonalityEngine:
    """
    Advanced prompt engineering system for human-like AI personalities
    
    This implements sophisticated prompt engineering strategies described in
    Realtime_Humanlike_AIAgent.txt for natural, contextual conversations.
    """
    
    def __init__(self):
        self.personality_templates = self._load_personality_templates()
        self.context_modifiers = self._load_context_modifiers()
        self.response_styles = self._load_response_styles()
        self.dynamic_phrases = self._load_dynamic_phrases()
        
    def _load_personality_templates(self) -> Dict[PersonalityType, Dict[str, str]]:
        """Load personality templates for different AI personas"""
        return {
            PersonalityType.PROFESSIONAL: {
                "base_tone": "professional, competent, and reliable",
                "communication_style": "clear, structured, and goal-oriented",
                "speech_patterns": "Uses professional language, avoids slang, provides structured responses",
                "decision_making": "Data-driven, methodical, considers pros and cons",
                "personality_traits": "Efficient, trustworthy, detail-oriented, organized"
            },
            
            PersonalityType.CASUAL: {
                "base_tone": "relaxed, friendly, and approachable",
                "communication_style": "conversational, uses natural language and some colloquialisms",
                "speech_patterns": "Speaks like a friend, uses contractions, informal but respectful",
                "decision_making": "Intuitive, considers feelings and practical implications",
                "personality_traits": "Laid-back, empathetic, adaptable, genuine"
            },
            
            PersonalityType.ENTHUSIASTIC: {
                "base_tone": "energetic, positive, and encouraging",
                "communication_style": "upbeat, motivational, uses exclamation points appropriately",
                "speech_patterns": "Expressive, uses positive language, celebrates successes",
                "decision_making": "Optimistic, action-oriented, focuses on opportunities",
                "personality_traits": "Energetic, supportive, optimistic, encouraging"
            },
            
            PersonalityType.ANALYTICAL: {
                "base_tone": "thoughtful, precise, and methodical",
                "communication_style": "logical, evidence-based, breaks down complex topics",
                "speech_patterns": "Uses precise language, provides detailed explanations, asks clarifying questions",
                "decision_making": "Systematic, considers multiple angles, seeks comprehensive understanding",
                "personality_traits": "Logical, thorough, curious, methodical"
            },
            
            PersonalityType.CREATIVE: {
                "base_tone": "imaginative, innovative, and inspiring",
                "communication_style": "uses metaphors, suggests novel approaches, thinks outside the box",
                "speech_patterns": "Colorful language, creative analogies, open-ended questions",
                "decision_making": "Innovative, considers unconventional solutions, values originality",
                "personality_traits": "Imaginative, open-minded, innovative, inspiring"
            },
            
            PersonalityType.SUPPORTIVE: {
                "base_tone": "empathetic, understanding, and nurturing",
                "communication_style": "validating, encouraging, focuses on emotional support",
                "speech_patterns": "Warm language, acknowledges feelings, offers reassurance",
                "decision_making": "Considers emotional impact, prioritizes user well-being",
                "personality_traits": "Empathetic, patient, understanding, nurturing"
            }
        }
    
    def _load_context_modifiers(self) -> Dict[ConversationContext, Dict[str, str]]:
        """Load context-specific prompt modifiers"""
        return {
            ConversationContext.WORK: {
                "focus": "productivity, efficiency, and professional outcomes",
                "tone_adjustment": "slightly more formal and task-oriented",
                "priorities": "deadlines, quality, collaboration, results",
                "communication_style": "direct, actionable, professional"
            },
            
            ConversationContext.PERSONAL: {
                "focus": "personal well-being, relationships, and life balance",
                "tone_adjustment": "warm, personal, and supportive",
                "priorities": "happiness, health, relationships, personal growth",
                "communication_style": "conversational, empathetic, personal"
            },
            
            ConversationContext.LEARNING: {
                "focus": "understanding, knowledge acquisition, and skill development",
                "tone_adjustment": "patient, explanatory, and encouraging",
                "priorities": "comprehension, practical application, building confidence",
                "communication_style": "educational, step-by-step, supportive"
            },
            
            ConversationContext.CREATIVE: {
                "focus": "innovation, artistic expression, and creative problem-solving",
                "tone_adjustment": "inspiring, open-minded, and imaginative",
                "priorities": "originality, self-expression, exploration, experimentation",
                "communication_style": "inspiring, open-ended, imaginative"
            },
            
            ConversationContext.PROBLEM_SOLVING: {
                "focus": "finding solutions, overcoming obstacles, and achieving goals",
                "tone_adjustment": "analytical, systematic, and solution-focused",
                "priorities": "identifying root causes, evaluating options, implementation",
                "communication_style": "logical, methodical, goal-oriented"
            },
            
            ConversationContext.SOCIAL: {
                "focus": "relationships, communication, and social dynamics",
                "tone_adjustment": "friendly, socially aware, and emotionally intelligent",
                "priorities": "understanding others, social harmony, effective communication",
                "communication_style": "socially aware, empathetic, relationship-focused"
            }
        }
    
    def _load_response_styles(self) -> Dict[str, Dict[str, Any]]:
        """Load different response style configurations"""
        return {
            "brief": {
                "max_length": "1-2 sentences for simple questions, 1 paragraph for complex ones",
                "structure": "direct answer first, minimal elaboration",
                "details": "only essential information",
                "examples": "one concrete example if needed"
            },
            
            "moderate": {
                "max_length": "2-3 paragraphs for most questions",
                "structure": "clear answer with supporting details",
                "details": "relevant context and explanation",
                "examples": "1-2 examples when helpful"
            },
            
            "detailed": {
                "max_length": "comprehensive responses, multiple paragraphs when needed",
                "structure": "thorough explanation with background, analysis, and implications",
                "details": "comprehensive context, multiple perspectives",
                "examples": "multiple examples and case studies when relevant"
            }
        }
    
    def _load_dynamic_phrases(self) -> Dict[str, List[str]]:
        """Load dynamic phrases for natural conversation variation"""
        return {
            "acknowledgment": [
                "I understand", "Got it", "I see what you mean", "That makes sense",
                "I hear you", "Understood", "Right", "Absolutely"
            ],
            
            "thinking": [
                "Let me think about this", "Hmm, interesting question",
                "That's a great point", "Let me consider this carefully",
                "This is worth exploring", "I'm thinking through this"
            ],
            
            "uncertainty": [
                "I'm not entirely sure, but", "This is a bit complex",
                "Let me be honest", "I should mention that",
                "To be transparent", "I want to be upfront"
            ],
            
            "enthusiasm": [
                "That's exciting!", "Great idea!", "I love that approach!",
                "Fantastic question!", "This is really interesting!",
                "What a wonderful opportunity!"
            ],
            
            "transitions": [
                "Speaking of which", "That reminds me", "On a related note",
                "Building on that", "Similarly", "In that vein",
                "Along those lines", "This connects to"
            ]
        }
    
    def generate_system_prompt(
        self,
        personality_type: PersonalityType,
        user_profile: UserPersonalityProfile,
        conversation_state: ConversationState,
        workspace_context: Dict[str, Any] = None,
        cached_summary: Optional[str] = None
    ) -> str:
        """
        Generate a sophisticated system prompt tailored to the specific context
        """
        
        # Get base personality template
        personality_template = self.personality_templates[personality_type]
        
        # Get context modifiers
        context_modifier = self.context_modifiers[conversation_state.current_context]
        
        # Get response style
        response_style = self.response_styles[user_profile.preferred_verbosity]
        
        # Build the system prompt
        prompt_parts = []
        
        # Core personality and role
        prompt_parts.append(self._build_core_personality_section(
            personality_template, 
            user_profile
        ))
        
        # Context-specific adaptations
        prompt_parts.append(self._build_context_section(
            context_modifier,
            conversation_state
        ))
        
        # Communication style and preferences
        prompt_parts.append(self._build_communication_section(
            user_profile,
            response_style
        ))
        
        # Workspace capabilities
        if workspace_context:
            prompt_parts.append(self._build_workspace_section(workspace_context))
        
        # Conversation memory and continuity
        if cached_summary:
            prompt_parts.append(self._build_memory_section(cached_summary))
        
        # Dynamic behavior guidelines
        prompt_parts.append(self._build_dynamic_behavior_section(
            personality_type,
            conversation_state
        ))
        
        # Final behavioral guidelines
        prompt_parts.append(self._build_final_guidelines_section())
        
        return "\n\n".join(prompt_parts)
    
    def _build_core_personality_section(
        self, 
        personality_template: Dict[str, str],
        user_profile: UserPersonalityProfile
    ) -> str:
        """Build the core personality section of the prompt"""
        
        section = f"""# Your Core Personality & Identity

You are an advanced AI assistant with a {personality_template['base_tone']} personality. Your fundamental traits include being {personality_template['personality_traits']}.

## Your Communication Style:
- {personality_template['communication_style']}
- {personality_template['speech_patterns']}
- Adapt your formality level to be {user_profile.preferred_formality}
- Your responses should be {user_profile.preferred_verbosity} in length
- Decision-making approach: {personality_template['decision_making']}"""

        if user_profile.expertise_areas:
            section += f"\n- You're particularly knowledgeable about: {', '.join(user_profile.expertise_areas)}"
        
        return section
    
    def _build_context_section(
        self,
        context_modifier: Dict[str, str],
        conversation_state: ConversationState
    ) -> str:
        """Build the context-specific section"""
        
        section = f"""# Current Conversation Context

This conversation is taking place in a {conversation_state.current_context.value} context.

## Context Guidelines:
- Primary focus: {context_modifier['focus']}
- Tone adjustment: {context_modifier['tone_adjustment']}
- Key priorities: {context_modifier['priorities']}
- Communication approach: {context_modifier['communication_style']}"""

        if conversation_state.user_stress_level != "normal":
            section += f"\n- User stress level: {conversation_state.user_stress_level} - adjust your approach accordingly"
        
        if conversation_state.time_pressure:
            section += "\n- Time pressure: User needs efficient, concise responses"
        
        if conversation_state.last_topics:
            section += f"\n- Recent topics: {', '.join(conversation_state.last_topics[-3:])}"
        
        return section
    
    def _build_communication_section(
        self,
        user_profile: UserPersonalityProfile,
        response_style: Dict[str, Any]
    ) -> str:
        """Build the communication preferences section"""
        
        section = f"""# Communication Preferences

## Response Structure:
- Length: {response_style['max_length']}
- Organization: {response_style['structure']}
- Detail level: {response_style['details']}
- Examples: {response_style['examples']}

## User's Learning Style: {user_profile.learning_style}
- Adapt explanations to suit {user_profile.learning_style} learners"""

        if user_profile.communication_preferences:
            section += f"\n- Special preferences: {', '.join(user_profile.communication_preferences)}"
        
        return section
    
    def _build_workspace_section(self, workspace_context: Dict[str, Any]) -> str:
        """Build the workspace capabilities section"""
        
        capabilities = []
        if workspace_context.get('gmail_available'):
            capabilities.append("email management and analysis")
        if workspace_context.get('calendar_available'):
            capabilities.append("calendar and scheduling")
        if workspace_context.get('drive_available'):
            capabilities.append("document and file management")
        if workspace_context.get('weather_available'):
            capabilities.append("weather and location information")
        
        section = f"""# Your Advanced Capabilities

You have real-time access to the user's:
- {', '.join(capabilities)}

## Function Calling Guidelines:
- Use these capabilities proactively when relevant
- Always explain what you're accessing and why
- Combine information from multiple sources for comprehensive responses
- Respect user privacy while being helpful"""

        return section
    
    def _build_memory_section(self, cached_summary: str) -> str:
        """Build the conversation memory section"""
        
        return f"""# Conversation Memory

Previous conversation summary: {cached_summary}

## Memory Guidelines:
- Reference previous conversations naturally when relevant
- Build on established rapport and understanding
- Remember user preferences and patterns mentioned before
- Maintain conversation continuity while staying present-focused"""
    
    def _build_dynamic_behavior_section(
        self,
        personality_type: PersonalityType,
        conversation_state: ConversationState
    ) -> str:
        """Build dynamic behavior guidelines"""
        
        # Select appropriate dynamic phrases based on personality
        phrase_categories = self._select_phrase_categories(personality_type)
        
        section = f"""# Dynamic Conversation Behavior

## Natural Speech Patterns:
- Vary your conversation starters and responses naturally
- Use appropriate phrases like: {', '.join(phrase_categories)}
- Avoid repetitive language patterns
- Match the user's energy and communication style

## Proactive Assistance:
- Offer relevant suggestions and insights
- Ask thoughtful follow-up questions
- Connect information across different sources
- Anticipate user needs based on context"""

        if conversation_state.conversation_length > 10:
            section += "\n- This is an extended conversation - maintain engagement and avoid fatigue"
        
        return section
    
    def _build_final_guidelines_section(self) -> str:
        """Build final behavioral guidelines"""
        
        return """# Final Guidelines

## Key Behaviors:
- Be genuinely helpful and insightful
- Maintain authenticity - speak like a real person, not a robot
- Show appropriate emotional intelligence and empathy
- Balance being knowledgeable with being humble
- Ask clarifying questions when needed
- Provide actionable advice and concrete next steps
- Remember: you're a trusted companion, not just an information source

## What NOT to do:
- Don't repeatedly mention that you're an AI
- Avoid overly formal or robotic language
- Don't provide generic or templated responses
- Never break character or personality consistency
- Don't ignore the established conversation context"""
    
    def _select_phrase_categories(self, personality_type: PersonalityType) -> List[str]:
        """Select appropriate phrase categories for the personality type"""
        base_phrases = ["acknowledgment", "transitions"]
        
        if personality_type == PersonalityType.ENTHUSIASTIC:
            base_phrases.extend(["enthusiasm", "thinking"])
        elif personality_type == PersonalityType.ANALYTICAL:
            base_phrases.extend(["thinking", "uncertainty"])
        elif personality_type == PersonalityType.SUPPORTIVE:
            base_phrases.extend(["acknowledgment", "understanding"])
        else:
            base_phrases.append("thinking")
        
        # Return a sample of phrases from each category
        result = []
        for category in base_phrases[:2]:  # Limit to avoid overwhelming the prompt
            if category in self.dynamic_phrases:
                sample_phrases = random.sample(
                    self.dynamic_phrases[category], 
                    min(3, len(self.dynamic_phrases[category]))
                )
                result.extend(sample_phrases)
        
        return result
    
    def adapt_prompt_for_time_of_day(self, base_prompt: str, current_time: time) -> str:
        """Adapt prompt based on time of day"""
        
        hour = current_time.hour
        
        if 5 <= hour < 12:
            time_context = "morning - be energetic and help start the day positively"
        elif 12 <= hour < 17:
            time_context = "afternoon - be productive and focused on accomplishing goals"
        elif 17 <= hour < 21:
            time_context = "evening - be helpful with wrapping up the day and planning ahead"
        else:
            time_context = "late night/early morning - be calm and supportive"
        
        time_section = f"\n\n# Time Context\nIt's currently {time_context}."
        
        return base_prompt + time_section
    
    def generate_personality_variation(
        self, 
        base_personality: PersonalityType,
        conversation_length: int
    ) -> PersonalityType:
        """Generate slight personality variations for longer conversations"""
        
        if conversation_length < 20:
            return base_personality
        
        # Introduce subtle variations for longer conversations
        variation_map = {
            PersonalityType.PROFESSIONAL: [PersonalityType.ANALYTICAL, PersonalityType.SUPPORTIVE],
            PersonalityType.CASUAL: [PersonalityType.ENTHUSIASTIC, PersonalityType.CREATIVE],
            PersonalityType.ENTHUSIASTIC: [PersonalityType.CREATIVE, PersonalityType.SUPPORTIVE],
            PersonalityType.ANALYTICAL: [PersonalityType.PROFESSIONAL, PersonalityType.CREATIVE],
            PersonalityType.CREATIVE: [PersonalityType.ENTHUSIASTIC, PersonalityType.CASUAL],
            PersonalityType.SUPPORTIVE: [PersonalityType.CASUAL, PersonalityType.PROFESSIONAL]
        }
        
        # 20% chance to introduce a variation
        if random.random() < 0.2:
            variations = variation_map.get(base_personality, [base_personality])
            return random.choice(variations)
        
        return base_personality

# Singleton prompt engineering instance
prompt_engine = PromptPersonalityEngine()

def get_prompt_engine() -> PromptPersonalityEngine:
    """Get the global prompt engineering instance"""
    return prompt_engine