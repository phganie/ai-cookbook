"""
Tests for LLM service (Vertex AI integration).
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas import RecipeLLMOutput
from app.services.llm import (
    _clean_model_text,
    build_user_prompt,
    call_llm_for_recipe,
    initialize_vertex_ai,
)


class TestHelperFunctions:
    """Test helper functions."""

    def test_build_user_prompt(self):
        """Test user prompt building."""
        transcript = "Test transcript"
        prompt = build_user_prompt(transcript)
        assert "TRANSCRIPT" in prompt
        assert transcript in prompt

    def test_clean_model_text_plain_json(self):
        """Test cleaning plain JSON text."""
        text = '{"title": "Test"}'
        result = _clean_model_text(text)
        assert result == '{"title": "Test"}'

    def test_clean_model_text_with_markdown(self):
        """Test cleaning JSON wrapped in markdown."""
        text = "```json\n{\"title\": \"Test\"}\n```"
        result = _clean_model_text(text)
        assert result == '{"title": "Test"}'

    def test_clean_model_text_with_code_block(self):
        """Test cleaning JSON in code block."""
        text = "```\n{\"title\": \"Test\"}\n```"
        result = _clean_model_text(text)
        assert result == '{"title": "Test"}'

    def test_clean_model_text_extract_json(self):
        """Test extracting JSON from mixed text."""
        text = "Here's the recipe:\n{\"title\": \"Test\"}\nThat's it!"
        result = _clean_model_text(text)
        assert result == '{"title": "Test"}'


class TestVertexAIIntegration:
    """Test Vertex AI initialization and configuration."""

    def setup_method(self):
        """Clear cache before each test."""
        # Only clear if cached
        if hasattr(initialize_vertex_ai, "cache_clear"):
            initialize_vertex_ai.cache_clear()

    @patch("google.cloud.aiplatform.init")
    @patch("app.services.llm.get_settings")
    def test_initialize_vertex_ai_success(self, mock_get_settings, mock_init):
        """Test successful Vertex AI initialization."""
        mock_settings = MagicMock()
        mock_settings.vertex_project_id = "test-project"
        mock_settings.vertex_location = "us-central1"
        mock_get_settings.return_value = mock_settings

        initialize_vertex_ai()

        mock_init.assert_called_once_with(
            project="test-project",
            location="us-central1",
        )

    @patch("app.services.llm.get_settings")
    def test_initialize_vertex_ai_missing_project(self, mock_get_settings):
        """Test initialization fails without project ID."""
        mock_settings = MagicMock()
        mock_settings.vertex_project_id = None
        mock_get_settings.return_value = mock_settings

        with pytest.raises(RuntimeError, match="VERTEX_PROJECT_ID is not set"):
            initialize_vertex_ai()


class TestLLMRecipeExtraction:
    """Test recipe extraction from transcripts."""

    @patch("app.services.llm.GenerativeModel")
    @patch("app.services.llm.initialize_vertex_ai")
    @patch("app.services.llm.get_settings")
    def test_call_llm_for_recipe_success(
        self, mock_get_settings, mock_init, mock_generative_model, sample_recipe_json
    ):
        """Test successful recipe extraction."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.vertex_project_id = "test-project"
        mock_settings.vertex_model = "gemini-1.5-flash"
        mock_get_settings.return_value = mock_settings

        # Mock Vertex AI response
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_recipe_json)

        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        # Call function
        result = call_llm_for_recipe("Test transcript")

        # Assertions
        assert isinstance(result, RecipeLLMOutput)
        assert result.title == "Chocolate Chip Cookies"
        assert result.servings == 24
        assert len(result.ingredients) == 4
        assert len(result.steps) == 4
        mock_model_instance.generate_content.assert_called_once()

    @patch("app.services.llm.GenerativeModel")
    @patch("app.services.llm.initialize_vertex_ai")
    @patch("app.services.llm.get_settings")
    def test_call_llm_for_recipe_with_markdown(
        self, mock_get_settings, mock_init, mock_generative_model, sample_recipe_json
    ):
        """Test recipe extraction with markdown-wrapped JSON."""
        mock_settings = MagicMock()
        mock_settings.vertex_project_id = "test-project"
        mock_settings.vertex_model = "gemini-1.5-flash"
        mock_get_settings.return_value = mock_settings

        # Response wrapped in markdown
        mock_response = MagicMock()
        mock_response.text = f"```json\n{json.dumps(sample_recipe_json)}\n```"

        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        result = call_llm_for_recipe("Test transcript")

        assert isinstance(result, RecipeLLMOutput)
        assert result.title == "Chocolate Chip Cookies"

    @patch("app.services.llm.GenerativeModel")
    @patch("app.services.llm.initialize_vertex_ai")
    @patch("app.services.llm.get_settings")
    def test_call_llm_for_recipe_empty_response(
        self, mock_get_settings, mock_init, mock_generative_model
    ):
        """Test handling of empty response."""
        mock_settings = MagicMock()
        mock_settings.vertex_project_id = "test-project"
        mock_settings.vertex_model = "gemini-1.5-flash"
        mock_get_settings.return_value = mock_settings

        mock_response = MagicMock()
        mock_response.text = ""

        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        with pytest.raises(RuntimeError, match="Failed to extract recipe"):
            call_llm_for_recipe("Test transcript", max_retries=1)

    @patch("app.services.llm.GenerativeModel")
    @patch("app.services.llm.initialize_vertex_ai")
    @patch("app.services.llm.get_settings")
    def test_call_llm_for_recipe_invalid_json(
        self, mock_get_settings, mock_init, mock_generative_model
    ):
        """Test handling of invalid JSON response."""
        mock_settings = MagicMock()
        mock_settings.vertex_project_id = "test-project"
        mock_settings.vertex_model = "gemini-1.5-flash"
        mock_get_settings.return_value = mock_settings

        mock_response = MagicMock()
        mock_response.text = "This is not JSON"

        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance

        with pytest.raises(RuntimeError, match="Failed to extract recipe"):
            call_llm_for_recipe("Test transcript", max_retries=1)

    @patch("app.services.llm.GenerativeModel")
    @patch("app.services.llm.initialize_vertex_ai")
    @patch("app.services.llm.get_settings")
    def test_call_llm_for_recipe_retry_on_error(
        self, mock_get_settings, mock_init, mock_generative_model, sample_recipe_json
    ):
        """Test retry logic on errors."""
        mock_settings = MagicMock()
        mock_settings.vertex_project_id = "test-project"
        mock_settings.vertex_model = "gemini-1.5-flash"
        mock_get_settings.return_value = mock_settings

        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_recipe_json)

        mock_model_instance = MagicMock()
        # First call fails, second succeeds
        mock_model_instance.generate_content.side_effect = [
            Exception("Network error"),
            mock_response,
        ]
        mock_generative_model.return_value = mock_model_instance

        result = call_llm_for_recipe("Test transcript", max_retries=2)

        assert isinstance(result, RecipeLLMOutput)
        assert mock_model_instance.generate_content.call_count == 2


@pytest.mark.integration
@pytest.mark.vertex_ai
class TestVertexAIIntegrationReal:
    """
    Integration tests that actually call Vertex AI.
    
    These tests require:
    - VERTEX_PROJECT_ID environment variable
    - Valid Google Cloud authentication
    - Vertex AI API enabled in the project
    
    Run with: pytest -m vertex_ai
    """

    def test_real_vertex_ai_call(self, sample_transcript):
        """Test actual Vertex AI call with a real transcript."""
        # Skip if credentials not available
        import os
        if os.getenv("RUN_VERTEX_INTEGRATION") != "1":
            pytest.skip("Set RUN_VERTEX_INTEGRATION=1 to run Vertex integration tests")

        if not os.getenv("VERTEX_PROJECT_ID"):
            pytest.skip("VERTEX_PROJECT_ID not set")

        result = call_llm_for_recipe(sample_transcript)
            
        # Verify the result structure
        assert isinstance(result, RecipeLLMOutput)
        assert result.title
        assert len(result.title) > 0
        assert isinstance(result.ingredients, list)
        assert isinstance(result.steps, list)
        assert len(result.steps) > 0

        # Verify ingredients have required fields
        for ing in result.ingredients:
            assert ing.name
            assert ing.source in ["explicit", "inferred"]
            assert ing.evidence.start_sec >= 0
            assert ing.evidence.end_sec >= ing.evidence.start_sec

        # Verify steps have required fields
        for step in result.steps:
            assert step.step_number > 0
            assert step.text
            assert step.start_sec >= 0
            assert step.end_sec >= step.start_sec
            assert step.evidence_quote
       