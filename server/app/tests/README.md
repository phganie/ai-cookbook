# CookClip Backend Tests

This directory contains tests for the CookClip backend.

## Running Tests

### Run all tests
```bash
pytest
```

### Run only unit tests (fast, no external dependencies)
```bash
pytest -m unit
```

### Run integration tests (may call external APIs)
```bash
pytest -m integration
```

### Run Vertex AI integration tests (requires credentials)
```bash
# Set up credentials first
export VERTEX_PROJECT_ID=your-project-id
gcloud auth application-default login

# Run tests
pytest -m vertex_ai
```

### Run with coverage report
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

### Run specific test file
```bash
pytest app/tests/test_llm.py
```

### Run specific test
```bash
pytest app/tests/test_llm.py::TestVertexAIIntegrationReal::test_real_vertex_ai_call
```

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_llm.py` - Tests for Vertex AI LLM service
- `test_api.py` - Tests for FastAPI endpoints
- `test_youtube.py` - Tests for YouTube transcript service
- `test_recipes.py` - Tests for recipe database operations

## Test Markers

- `@pytest.mark.unit` - Unit tests (fast, mocked)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.vertex_ai` - Tests requiring Vertex AI credentials
- `@pytest.mark.slow` - Tests that take a long time

## Testing Vertex AI

To test that Vertex AI actually works:

1. **Set up credentials:**
   ```bash
   export VERTEX_PROJECT_ID=your-gcp-project-id
   gcloud auth application-default login
   ```

2. **Run the integration test:**
   ```bash
   pytest -m vertex_ai -v
   ```

3. **Check the output:** The test will make a real call to Vertex AI and verify:
   - The response is valid JSON
   - The response matches the RecipeLLMOutput schema
   - All required fields are present
   - Data types are correct

## Writing New Tests

1. Create test files with `test_` prefix
2. Use fixtures from `conftest.py` (e.g., `test_db`, `client`, `sample_recipe_json`)
3. Mark tests appropriately (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
4. Mock external dependencies for unit tests
5. Use real APIs for integration tests (with proper markers)

## Example Test

```python
import pytest
from unittest.mock import patch

@pytest.mark.unit
def test_my_function(mock_settings):
    """Test my function with mocked dependencies."""
    with patch("app.services.my_service.external_api") as mock_api:
        mock_api.return_value = "expected_result"
        result = my_function()
        assert result == "expected_result"
```

