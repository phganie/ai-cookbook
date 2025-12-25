"""
Pytest fixtures and configuration for all tests.
"""
import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create a temporary SQLite database for testing."""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        os.unlink(db_path)


@pytest.fixture
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with dependency overrides."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_settings(monkeypatch) -> Settings:
    """Create mock settings for testing."""
    settings = Settings(
        vertex_project_id="test-project",
        vertex_location="us-central1",
        vertex_model="gemini-2.5-flash",
        database_url="sqlite:///./test.db",
        youtube_cookie=None,
        environment="test",
    )
    
    # Clear the cache to ensure fresh settings
    get_settings.cache_clear()
    
    # Monkeypatch environment variables
    monkeypatch.setenv("VERTEX_PROJECT_ID", "test-project")
    monkeypatch.setenv("VERTEX_LOCATION", "us-central1")
    monkeypatch.setenv("VERTEX_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("ENVIRONMENT", "test")
    
    return settings


@pytest.fixture
def sample_transcript() -> str:
    """Sample YouTube transcript for testing."""
    return """
    Welcome to my cooking channel! Today we're making chocolate chip cookies.
    First, we need 2 cups of all-purpose flour. Then add 1 cup of sugar.
    Mix in 2 eggs and half a cup of butter. 
    Preheat your oven to 350 degrees Fahrenheit.
    Bake for 12 minutes until golden brown.
    Let them cool for 5 minutes before serving.
    This recipe makes about 24 cookies.
    """


@pytest.fixture
def sample_recipe_json() -> dict:
    """Sample recipe JSON matching the schema."""
    return {
        "title": "Chocolate Chip Cookies",
        "servings": 24,
        "ingredients": [
            {
                "name": "all-purpose flour",
                "amount": 2.0,
                "unit": "cups",
                "prep": None,
                "source": "explicit",
                "evidence": {
                    "start_sec": 5.0,
                    "end_sec": 7.0,
                    "quote": "2 cups of all-purpose flour"
                }
            },
            {
                "name": "sugar",
                "amount": 1.0,
                "unit": "cup",
                "prep": None,
                "source": "explicit",
                "evidence": {
                    "start_sec": 8.0,
                    "end_sec": 9.0,
                    "quote": "1 cup of sugar"
                }
            },
            {
                "name": "eggs",
                "amount": 2.0,
                "unit": None,
                "prep": None,
                "source": "explicit",
                "evidence": {
                    "start_sec": 10.0,
                    "end_sec": 11.0,
                    "quote": "2 eggs"
                }
            },
            {
                "name": "butter",
                "amount": 0.5,
                "unit": "cup",
                "prep": None,
                "source": "explicit",
                "evidence": {
                    "start_sec": 11.0,
                    "end_sec": 12.0,
                    "quote": "half a cup of butter"
                }
            }
        ],
        "steps": [
            {
                "step_number": 1,
                "text": "Mix 2 cups of all-purpose flour with 1 cup of sugar",
                "start_sec": 5.0,
                "end_sec": 9.0,
                "evidence_quote": "2 cups of all-purpose flour. Then add 1 cup of sugar"
            },
            {
                "step_number": 2,
                "text": "Add 2 eggs and half a cup of butter",
                "start_sec": 10.0,
                "end_sec": 12.0,
                "evidence_quote": "Mix in 2 eggs and half a cup of butter"
            },
            {
                "step_number": 3,
                "text": "Preheat oven to 350 degrees Fahrenheit",
                "start_sec": 13.0,
                "end_sec": 14.0,
                "evidence_quote": "Preheat your oven to 350 degrees Fahrenheit"
            },
            {
                "step_number": 4,
                "text": "Bake for 12 minutes until golden brown",
                "start_sec": 15.0,
                "end_sec": 16.0,
                "evidence_quote": "Bake for 12 minutes until golden brown"
            }
        ],
        "missing_info": [],
        "notes": ["Let cookies cool for 5 minutes before serving"]
    }

