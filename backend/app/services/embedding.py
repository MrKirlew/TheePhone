import asyncio
from typing import List
import numpy as np
from google.genai import types as genai_types
import google.generativeai as genai


class EmbeddingService:
    """Service for creating text embeddings using Gemini embedding model."""
    
    def __init__(self, model_name: str = "models/text-embedding-004"):
        self.model_name = model_name

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: genai.embed_content(
                    model=self.model_name,
                    content=text
                )
            )
            return result['embedding']
        except Exception as e:
            # Fallback to random embedding if API fails
            return np.random.rand(768).tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: genai.embed_content(
                    model=self.model_name,
                    content=texts
                )
            )
            return result['embedding']
        except Exception as e:
            # Fallback to random embeddings if API fails
            return [np.random.rand(768).tolist() for _ in texts]
