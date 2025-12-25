import os
from functools import lru_cache
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env only for local development
# Use override=True to ensure .env values take precedence over shell env vars
if os.getenv("ENVIRONMENT", "development") == "development":
    load_dotenv(override=True)


class Settings(BaseModel):
    # Vertex AI Configuration
    vertex_project_id: str | None = None
    vertex_location: str = "us-central1"
    vertex_model: str = "gemini-2.0-flash"  # Updated: use supported model

    # App config
    database_url: str
    youtube_cookie: str | None = None
    environment: str = "development"

    # Audio transcription fallback
    enable_audio_fallback: bool = False
    # Separate flag for audio transcription (disabled in production by default)
    enable_audio_transcription: bool = False
    gcp_project_id: str | None = None
    gcp_location: str = "us-central1"
    stt_language_code: str = "en-US"
    stt_model: str | None = None
    stt_max_audio_seconds: int = 600
    
    # Authentication
    secret_key: str = Field(default="your-secret-key-change-in-production-min-32-chars")
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None


@lru_cache
def get_settings() -> Settings:
    # Reuse VERTEX_PROJECT_ID for GCP if GCP_PROJECT_ID not set
    vertex_project_id = os.getenv("VERTEX_PROJECT_ID")
    gcp_project_id = os.getenv("GCP_PROJECT_ID") or vertex_project_id
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Loading settings: VERTEX_PROJECT_ID=%s (from env: %s), GCP_PROJECT_ID=%s", 
                 vertex_project_id, os.getenv("VERTEX_PROJECT_ID"), gcp_project_id)
    
    return Settings(
        vertex_project_id=vertex_project_id,
        vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        vertex_model=os.getenv("VERTEX_MODEL", "gemini-2.0-flash").lower(),  # Normalize to lowercase
        database_url=os.getenv(
            "DATABASE_URL",
            "sqlite:///./cookclip.db",
        ),
        youtube_cookie=os.getenv("YOUTUBE_COOKIE"),
        environment=os.getenv("ENVIRONMENT", "development"),
        enable_audio_fallback=os.getenv("ENABLE_AUDIO_FALLBACK", "0") == "1",
        enable_audio_transcription=os.getenv("ENABLE_AUDIO_TRANSCRIPTION", "0") == "1",
        gcp_project_id=gcp_project_id,
        gcp_location=os.getenv("GCP_LOCATION", "us-central1"),
        stt_language_code=os.getenv("STT_LANGUAGE_CODE", "en-US"),
        stt_model=os.getenv("STT_MODEL") or None,
        stt_max_audio_seconds=int(os.getenv("STT_MAX_AUDIO_SECONDS", "600")),
        secret_key=os.getenv("SECRET_KEY", "your-secret-key-change-in-production-min-32-chars"),
        google_oauth_client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        google_oauth_redirect_uri=os.getenv("GOOGLE_OAUTH_REDIRECT_URI"),
    )