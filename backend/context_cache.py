# context_cache.py - Context Caching for Long Conversations

import asyncio
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import aioredis
from dataclasses import dataclass, asdict
import tiktoken

# Google Cloud imports for context caching
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Content, Part
    from google.cloud import storage
    SERVICES_AVAILABLE = True
except ImportError as e:
    logging.error(f"Required libraries not available: {e}")
    SERVICES_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class CachedContext:
    """Represents a cached conversation context"""
    cache_id: str
    user_id: str
    conversation_id: str
    token_count: int
    created_at: datetime
    expires_at: datetime
    context_summary: str
    cached_content: List[Dict[str, Any]]
    cache_token: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if the cached context has expired"""
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedContext':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)

class ContextCacheManager:
    """
    Advanced context caching system for long conversations
    
    This implements caching strategies to reduce costs and improve response times
    for extended AI conversations as described in Realtime_Humanlike_AIAgent.txt
    """
    
    def __init__(self, project_id: str, ttl_hours: int = 24, max_cache_size: int = 50000):
        self.project_id = project_id
        self.ttl_hours = ttl_hours
        self.max_cache_size = max_cache_size
        
        # Initialize tokenizer for counting tokens
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
            logger.warning("tiktoken not available, using rough token estimation")
        
        # Storage backends
        self.redis_client: Optional[aioredis.Redis] = None
        self.storage_client = None
        self.cache_bucket = f"{project_id}-context-cache"
        
        # In-memory cache for frequently accessed contexts
        self.memory_cache: Dict[str, CachedContext] = {}
        self.max_memory_cache_size = 10
        
        # Context analysis
        self.context_analyzer = ContextAnalyzer()
        
    async def initialize(self):
        """Initialize the caching system"""
        try:
            # Initialize Redis connection (optional)
            await self._setup_redis()
            
            # Initialize Google Cloud Storage (optional)
            await self._setup_cloud_storage()
            
            logger.info("Context cache manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize context cache manager: {e}")
            # Continue without external storage
    
    async def _setup_redis(self):
        """Setup Redis connection for fast context caching"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = await aioredis.from_url(redis_url)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established for context caching")
            
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
            self.redis_client = None
    
    async def _setup_cloud_storage(self):
        """Setup Google Cloud Storage for persistent context caching"""
        try:
            if not SERVICES_AVAILABLE:
                return
                
            self.storage_client = storage.Client(project=self.project_id)
            
            # Ensure bucket exists
            try:
                bucket = self.storage_client.bucket(self.cache_bucket)
                if not bucket.exists():
                    bucket = self.storage_client.create_bucket(self.cache_bucket)
                    logger.info(f"Created context cache bucket: {self.cache_bucket}")
            except Exception as e:
                logger.warning(f"Could not setup storage bucket: {e}")
                self.storage_client = None
                
        except Exception as e:
            logger.warning(f"Cloud Storage not available for caching: {e}")
            self.storage_client = None
    
    def _count_tokens(self, content: str) -> int:
        """Count tokens in content"""
        if self.tokenizer:
            return len(self.tokenizer.encode(content))
        else:
            # Rough estimation: ~4 characters per token
            return len(content) // 4
    
    def _generate_cache_id(self, user_id: str, conversation_context: List[Dict[str, Any]]) -> str:
        """Generate a unique cache ID based on conversation content"""
        # Create hash of conversation content for deduplication
        content_str = json.dumps(conversation_context, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        return f"{user_id}_{content_hash}"
    
    async def should_cache_context(self, conversation_history: List[Dict[str, Any]]) -> bool:
        """Determine if conversation context should be cached"""
        if not conversation_history:
            return False
        
        # Count total tokens in conversation
        total_content = " ".join([
            msg.get('content', '') for msg in conversation_history
            if isinstance(msg.get('content'), str)
        ])
        token_count = self._count_tokens(total_content)
        
        # Cache if conversation is long enough and contains valuable context
        if token_count > 5000:  # Cache conversations over 5K tokens
            return True
        
        # Cache if conversation has function calls (valuable workspace context)
        has_function_calls = any(
            'function_call' in msg or 'tool_calls' in msg 
            for msg in conversation_history
        )
        
        if has_function_calls and token_count > 1000:
            return True
        
        return False
    
    async def create_cached_context(
        self, 
        user_id: str, 
        conversation_id: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Optional[CachedContext]:
        """Create a new cached context from conversation history"""
        try:
            cache_id = self._generate_cache_id(user_id, conversation_history)
            
            # Check if already cached
            existing_cache = await self.get_cached_context(cache_id)
            if existing_cache and not existing_cache.is_expired():
                return existing_cache
            
            # Analyze and summarize context
            context_summary = await self.context_analyzer.summarize_conversation(
                conversation_history
            )
            
            # Compress conversation history while preserving important parts
            compressed_history = await self.context_analyzer.compress_conversation(
                conversation_history, 
                max_tokens=self.max_cache_size
            )
            
            # Count tokens
            total_content = json.dumps(compressed_history)
            token_count = self._count_tokens(total_content)
            
            # Create cached context
            cached_context = CachedContext(
                cache_id=cache_id,
                user_id=user_id,
                conversation_id=conversation_id,
                token_count=token_count,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=self.ttl_hours),
                context_summary=context_summary,
                cached_content=compressed_history
            )
            
            # Store the context
            await self._store_cached_context(cached_context)
            
            logger.info(f"Created cached context {cache_id} with {token_count} tokens")
            return cached_context
            
        except Exception as e:
            logger.error(f"Failed to create cached context: {e}")
            return None
    
    async def get_cached_context(self, cache_id: str) -> Optional[CachedContext]:
        """Retrieve cached context by ID"""
        try:
            # Check memory cache first
            if cache_id in self.memory_cache:
                cached_context = self.memory_cache[cache_id]
                if not cached_context.is_expired():
                    return cached_context
                else:
                    del self.memory_cache[cache_id]
            
            # Check Redis cache
            if self.redis_client:
                cached_data = await self.redis_client.get(f"context:{cache_id}")
                if cached_data:
                    cached_context = CachedContext.from_dict(json.loads(cached_data))
                    if not cached_context.is_expired():
                        # Store in memory cache
                        self._update_memory_cache(cache_id, cached_context)
                        return cached_context
            
            # Check Cloud Storage
            if self.storage_client:
                cached_context = await self._load_from_storage(cache_id)
                if cached_context and not cached_context.is_expired():
                    # Store in faster caches
                    await self._store_cached_context(cached_context)
                    return cached_context
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached context {cache_id}: {e}")
            return None
    
    async def _store_cached_context(self, cached_context: CachedContext):
        """Store cached context in all available storage backends"""
        try:
            # Store in memory cache
            self._update_memory_cache(cached_context.cache_id, cached_context)
            
            # Store in Redis
            if self.redis_client:
                await self.redis_client.setex(
                    f"context:{cached_context.cache_id}",
                    int(timedelta(hours=self.ttl_hours).total_seconds()),
                    json.dumps(cached_context.to_dict())
                )
            
            # Store in Cloud Storage for persistence
            if self.storage_client:
                await self._save_to_storage(cached_context)
                
        except Exception as e:
            logger.error(f"Failed to store cached context: {e}")
    
    def _update_memory_cache(self, cache_id: str, cached_context: CachedContext):
        """Update in-memory cache with LRU eviction"""
        # Remove expired entries
        expired_keys = [
            key for key, context in self.memory_cache.items()
            if context.is_expired()
        ]
        for key in expired_keys:
            del self.memory_cache[key]
        
        # Add new context
        self.memory_cache[cache_id] = cached_context
        
        # Enforce size limit (simple LRU)
        if len(self.memory_cache) > self.max_memory_cache_size:
            # Remove oldest entry
            oldest_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k].created_at
            )
            del self.memory_cache[oldest_key]
    
    async def _save_to_storage(self, cached_context: CachedContext):
        """Save cached context to Google Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.cache_bucket)
            blob = bucket.blob(f"contexts/{cached_context.cache_id}.json")
            
            blob.upload_from_string(
                json.dumps(cached_context.to_dict()),
                content_type='application/json'
            )
            
        except Exception as e:
            logger.error(f"Failed to save context to storage: {e}")
    
    async def _load_from_storage(self, cache_id: str) -> Optional[CachedContext]:
        """Load cached context from Google Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.cache_bucket)
            blob = bucket.blob(f"contexts/{cache_id}.json")
            
            if blob.exists():
                data = json.loads(blob.download_as_text())
                return CachedContext.from_dict(data)
                
        except Exception as e:
            logger.error(f"Failed to load context from storage: {e}")
        
        return None
    
    async def cleanup_expired_contexts(self):
        """Clean up expired cached contexts"""
        try:
            # Clean memory cache
            expired_keys = [
                key for key, context in self.memory_cache.items()
                if context.is_expired()
            ]
            for key in expired_keys:
                del self.memory_cache[key]
            
            logger.info(f"Cleaned up {len(expired_keys)} expired contexts from memory")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired contexts: {e}")

class ContextAnalyzer:
    """Analyzes conversation context for compression and summarization"""
    
    def __init__(self):
        self.important_message_types = {
            'function_call', 'tool_calls', 'assistant', 'system'
        }
    
    async def summarize_conversation(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Create a summary of the conversation for quick reference"""
        try:
            # Extract key information
            user_messages = [
                msg for msg in conversation_history 
                if msg.get('role') == 'user'
            ]
            
            function_calls = [
                msg for msg in conversation_history
                if 'function_call' in msg or 'tool_calls' in msg
            ]
            
            # Create summary
            summary_parts = []
            
            if user_messages:
                recent_user_msg = user_messages[-1].get('content', '')[:200]
                summary_parts.append(f"User topic: {recent_user_msg}")
            
            if function_calls:
                function_names = [
                    self._extract_function_name(call) for call in function_calls[-3:]
                ]
                summary_parts.append(f"Recent functions: {', '.join(function_names)}")
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")
            return "Conversation summary unavailable"
    
    async def compress_conversation(
        self, 
        conversation_history: List[Dict[str, Any]], 
        max_tokens: int
    ) -> List[Dict[str, Any]]:
        """Compress conversation while preserving important context"""
        try:
            if not conversation_history:
                return []
            
            # Prioritize different message types
            compressed = []
            
            # Always keep system messages
            system_messages = [
                msg for msg in conversation_history 
                if msg.get('role') == 'system'
            ]
            compressed.extend(system_messages)
            
            # Keep recent function calls and their results
            recent_function_messages = [
                msg for msg in conversation_history[-20:]
                if ('function_call' in msg or 'tool_calls' in msg or 
                    msg.get('role') == 'function')
            ]
            compressed.extend(recent_function_messages)
            
            # Keep recent conversation (last 10 exchanges)
            recent_conversation = [
                msg for msg in conversation_history[-20:]
                if msg.get('role') in ['user', 'assistant'] and 
                'function_call' not in msg and 'tool_calls' not in msg
            ]
            compressed.extend(recent_conversation)
            
            # Remove duplicates while preserving order
            seen = set()
            deduplicated = []
            for msg in compressed:
                msg_id = hash(json.dumps(msg, sort_keys=True))
                if msg_id not in seen:
                    seen.add(msg_id)
                    deduplicated.append(msg)
            
            return deduplicated
            
        except Exception as e:
            logger.error(f"Failed to compress conversation: {e}")
            return conversation_history[-10:]  # Fallback to recent messages
    
    def _extract_function_name(self, message: Dict[str, Any]) -> str:
        """Extract function name from function call message"""
        try:
            if 'function_call' in message:
                return message['function_call'].get('name', 'unknown')
            elif 'tool_calls' in message:
                tool_calls = message['tool_calls']
                if tool_calls and isinstance(tool_calls, list):
                    return tool_calls[0].get('function', {}).get('name', 'unknown')
            return 'unknown'
        except Exception:
            return 'unknown'

# Context cache singleton
context_cache_manager: Optional[ContextCacheManager] = None

def get_context_cache_manager() -> Optional[ContextCacheManager]:
    """Get the global context cache manager instance"""
    return context_cache_manager

def initialize_context_cache(project_id: str, **kwargs) -> ContextCacheManager:
    """Initialize the global context cache manager"""
    global context_cache_manager
    context_cache_manager = ContextCacheManager(project_id, **kwargs)
    return context_cache_manager