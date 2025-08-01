"""
Gemini AI Service for Multimodal Processing
"""

import os
import logging
import json
import base64
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from PIL import Image
import io

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google's Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini service with API key"""
        # Use provided API key or get from environment
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not provided")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize models
        self.vision_model = genai.GenerativeModel('gemini-pro-vision')
        self.text_model = genai.GenerativeModel('gemini-pro')
        
        logger.info("Gemini service initialized successfully")
    
    async def process_multimodal_request(
        self,
        text_input: str,
        image_data: Optional[bytes] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process multimodal request with text and optional image
        
        Args:
            text_input: User's text/voice command
            image_data: Optional image bytes
            context: Optional context information (user email, session, etc.)
            
        Returns:
            Dict containing the AI response and metadata
        """
        try:
            if image_data:
                # Process with vision model for multimodal input
                response = await self._process_with_vision(text_input, image_data, context)
            else:
                # Process with text model for text-only input
                response = await self._process_text_only(text_input, context)
            
            return {
                'success': True,
                'response': response,
                'model_used': 'gemini-pro-vision' if image_data else 'gemini-pro',
                'has_image': image_data is not None
            }
            
        except Exception as e:
            logger.error(f"Error processing multimodal request: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': "I apologize, but I encountered an error processing your request."
            }
    
    async def _process_with_vision(
        self,
        text_input: str,
        image_data: bytes,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process request with vision model"""
        try:
            # Convert image bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Create enhanced prompt with context
            prompt = self._build_prompt(text_input, context, has_image=True)
            
            # Generate response with vision model
            response = self.vision_model.generate_content([prompt, image])
            
            # Extract and clean response text
            response_text = response.text
            
            logger.info(f"Vision model response generated, length: {len(response_text)}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error in vision processing: {e}")
            raise
    
    async def _process_text_only(
        self,
        text_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process text-only request"""
        try:
            # Create enhanced prompt with context
            prompt = self._build_prompt(text_input, context, has_image=False)
            
            # Generate response with text model
            response = self.text_model.generate_content(prompt)
            
            # Extract and clean response text
            response_text = response.text
            
            logger.info(f"Text model response generated, length: {len(response_text)}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error in text processing: {e}")
            raise
    
    def _build_prompt(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        has_image: bool = False
    ) -> str:
        """Build enhanced prompt with context and instructions"""
        
        # Base system prompt
        system_prompt = """You are KirlewAI, a helpful and friendly AI assistant. 
        You should provide accurate, helpful, and concise responses.
        Always be respectful and professional."""
        
        # Add context if available
        if context:
            if 'user_email' in context:
                system_prompt += f"\nUser: {context['user_email']}"
            if 'session_id' in context:
                system_prompt += f"\nSession: {context['session_id']}"
        
        # Add image-specific instructions
        if has_image:
            system_prompt += """\n
            The user has provided an image along with their request.
            Please analyze the image carefully and incorporate your observations
            into your response. Be specific about what you see in the image."""
        
        # Combine system prompt with user input
        full_prompt = f"{system_prompt}\n\nUser request: {user_input}"
        
        return full_prompt
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text using Gemini"""
        try:
            prompt = f"""Analyze the sentiment of the following text and provide:
            1. Overall sentiment (positive, negative, neutral)
            2. Confidence score (0-1)
            3. Key emotions detected
            
            Text: {text}
            
            Respond in JSON format."""
            
            response = self.text_model.generate_content(prompt)
            
            # Parse JSON response
            try:
                sentiment_data = json.loads(response.text)
            except:
                # Fallback if JSON parsing fails
                sentiment_data = {
                    'sentiment': 'neutral',
                    'confidence': 0.5,
                    'emotions': ['unknown']
                }
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                'sentiment': 'error',
                'confidence': 0,
                'emotions': [],
                'error': str(e)
            }
    
    def generate_contextual_response(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """Generate response considering conversation history"""
        try:
            # Build conversation context
            context_prompt = "Previous conversation:\n"
            if conversation_history:
                for turn in conversation_history[-5:]:  # Last 5 turns
                    role = turn.get('role', 'user')
                    content = turn.get('content', '')
                    context_prompt += f"{role}: {content}\n"
            
            # Add current user input
            full_prompt = f"{context_prompt}\nUser: {user_input}\nAssistant:"
            
            # Generate response
            response = self.text_model.generate_content(full_prompt)
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return "I apologize, but I'm having trouble generating a response right now."
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text"""
        try:
            prompt = f"""Extract the following entities from the text:
            - People names
            - Locations
            - Organizations
            - Dates/Times
            - Products
            - Other important entities
            
            Text: {text}
            
            Respond in JSON format with entity types as keys and lists of entities as values."""
            
            response = self.text_model.generate_content(prompt)
            
            # Parse JSON response
            try:
                entities = json.loads(response.text)
            except:
                entities = {}
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {}
    
    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """Summarize long text"""
        try:
            prompt = f"""Summarize the following text in approximately {max_length} characters:
            
            {text}
            
            Summary:"""
            
            response = self.text_model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error summarizing text: {e}")
            return "Unable to generate summary."
    
    def safety_check(self, content: str) -> Dict[str, Any]:
        """Check content for safety issues"""
        try:
            prompt = f"""Analyze the following content for safety issues:
            - Harmful content
            - Personal information exposure
            - Inappropriate language
            - Potential security risks
            
            Content: {content}
            
            Provide a safety score (0-1, where 1 is safest) and list any concerns in JSON format."""
            
            response = self.text_model.generate_content(prompt)
            
            try:
                safety_data = json.loads(response.text)
            except:
                safety_data = {
                    'safety_score': 0.5,
                    'concerns': ['Unable to parse safety check']
                }
            
            return safety_data
            
        except Exception as e:
            logger.error(f"Error performing safety check: {e}")
            return {
                'safety_score': 0,
                'concerns': ['Error during safety check'],
                'error': str(e)
            }