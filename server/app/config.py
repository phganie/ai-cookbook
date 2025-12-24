import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from the server directory (for local dev)
load_dotenv()


class Settings(BaseModel):
    openai_api_key: str | None = None
    database_url: str
    youtube_cookie: str | None = None
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        # Default to SQLite for local dev if DATABASE_URL not set
        database_url=os.getenv(
            "DATABASE_URL",
            "sqlite:///./cookclip.db",
        ),
        youtube_cookie=os.getenv("YOUTUBE_COOKIE"),
        environment=os.getenv("ENVIRONMENT", "development"),
    )


