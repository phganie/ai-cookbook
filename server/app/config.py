import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from the server directory (for local dev)
load_dotenv()


class Settings(BaseModel):
    # Vertex AI Configuration
    vertex_project_id: str | None = None
    vertex_location: str | None = None
    vertex_model: str = "gemini-1.5-flash"
    database_url: str
    youtube_cookie: str | None = None
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        vertex_project_id=os.getenv("VERTEX_PROJECT_ID"),
        vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        vertex_model=os.getenv("VERTEX_MODEL", "gemini-1.5-flash"),
        # Default to SQLite for local dev if DATABASE_URL not set
        database_url=os.getenv(
            "DATABASE_URL",
            "sqlite:///./cookclip.db",
        ),
        youtube_cookie=os.getenv("YOUTUBE_COOKIE"),
        environment=os.getenv("ENVIRONMENT", "development"),
    )


