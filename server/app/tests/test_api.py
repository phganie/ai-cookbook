"""
Tests for API endpoints.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.schemas import RecipeLLMOutput
from app.services import recipes as recipe_service


class TestExtractEndpoint:
    """Test /api/extract endpoint."""

    @patch("app.main.get_youtube_transcript")
    @patch("app.main.call_llm_for_recipe")
    def test_extract_recipe_success(
        self, mock_llm, mock_transcript, client: TestClient, sample_recipe_json
    ):
        """Test successful recipe extraction."""
        # Mock transcript
        mock_transcript.return_value = ("Test transcript", [])

        # Mock LLM response
        mock_recipe = RecipeLLMOutput.model_validate(sample_recipe_json)
        mock_llm.return_value = mock_recipe

        # Make request
        response = client.post(
            "/api/extract",
            json={"url": "https://www.youtube.com/watch?v=test123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Chocolate Chip Cookies"
        assert data["servings"] == 24

    @patch("app.main.get_youtube_transcript")
    def test_extract_recipe_invalid_url(self, mock_transcript, client: TestClient):
        """Test extraction with invalid URL."""
        mock_transcript.side_effect = ValueError("Could not parse YouTube video id")

        response = client.post(
            "/api/extract",
            json={"url": "not-a-valid-url"},
        )

        assert response.status_code == 400
        assert "Could not parse" in response.json()["detail"]

    @patch("app.main.get_youtube_transcript")
    @patch("app.main.call_llm_for_recipe")
    def test_extract_recipe_llm_failure(
        self, mock_llm, mock_transcript, client: TestClient
    ):
        """Test extraction when LLM fails."""
        mock_transcript.return_value = ("Test transcript", [])
        mock_llm.side_effect = Exception("LLM error")

        response = client.post(
            "/api/extract",
            json={"url": "https://www.youtube.com/watch?v=test123"},
        )

        assert response.status_code == 500
        assert "Failed to extract recipe" in response.json()["detail"]


class TestRecipesEndpoints:
    """Test recipe CRUD endpoints."""

    def test_create_recipe(self, client: TestClient, sample_recipe_json):
        """Test creating a recipe."""
        payload = {
            "source_url": "https://www.youtube.com/watch?v=test123",
            "source_platform": "youtube",
            "data": sample_recipe_json,
        }

        response = client.post("/api/recipes", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Chocolate Chip Cookies"
        assert data["id"]
        assert data["source_url"] == payload["source_url"]

    def test_list_recipes(self, client: TestClient, sample_recipe_json):
        """Test listing recipes."""
        # Create a recipe first
        payload = {
            "source_url": "https://www.youtube.com/watch?v=test123",
            "source_platform": "youtube",
            "data": sample_recipe_json,
        }
        client.post("/api/recipes", json=payload)

        # List recipes
        response = client.get("/api/recipes")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["title"] == "Chocolate Chip Cookies"

    def test_get_recipe_by_id(self, client: TestClient, sample_recipe_json):
        """Test getting a recipe by ID."""
        # Create a recipe
        payload = {
            "source_url": "https://www.youtube.com/watch?v=test123",
            "source_platform": "youtube",
            "data": sample_recipe_json,
        }
        create_response = client.post("/api/recipes", json=payload)
        recipe_id = create_response.json()["id"]

        # Get recipe
        response = client.get(f"/api/recipes/{recipe_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == recipe_id
        assert data["title"] == "Chocolate Chip Cookies"

    def test_get_recipe_not_found(self, client: TestClient):
        """Test getting a non-existent recipe."""
        response = client.get("/api/recipes/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

