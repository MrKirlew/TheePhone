import os

class Settings:
    project_id: str = os.getenv("PROJECT_ID", "twothreeatefi")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    map_api_key: str = os.getenv("MAP_API_KEY", "")
    owm_api_key: str = os.getenv("OWM_API_KEY", "")
    gemini_model_default: str = os.getenv("GEMINI_MODEL_DEFAULT", "gemini-2.0-flash")
    gemini_model_advanced: str = os.getenv("GEMINI_MODEL_ADVANCED", "gemini-2.0-pro-exp")
    gemini_embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
    firestore_collection_sessions: str = "adk_sessions"
    firestore_collection_memory: str = "adk_user_memory"
    firestore_collection_feedback: str = "adk_feedback"
    max_daily_requests: int = int(os.getenv("MAX_DAILY_REQUESTS", "500"))
    enable_vision_api: bool = os.getenv("ENABLE_VISION_API", "false").lower() == "true"

settings = Settings()