import google.generativeai as genai
from typing import List

# Uses Gemini Embedding model
EMBED_MODEL = "text-embedding-004"

def embed_text(text: str) -> List[float]:
    # Single-pass embedding
    resp = genai.embed_content(model=EMBED_MODEL, content=text)
    return resp["embedding"]