"""
Tests for recipe service (database operations).
"""
import pytest
from sqlalchemy.orm import Session

from app.models import Recipe
from app.schemas import RecipeLLMOutput
from app.services import recipes as recipe_service


class TestRecipeService:
    """Test recipe database operations."""

    def test_create_recipe(self, test_db: Session, sample_recipe_json):
        """Test creating a recipe in the database."""
        recipe_data = RecipeLLMOutput.model_validate(sample_recipe_json)

        recipe = recipe_service.create_recipe(
            db=test_db,
            source_url="https://www.youtube.com/watch?v=test123",
            source_platform="youtube",
            data=recipe_data,
        )

        assert recipe.id
        assert recipe.title == "Chocolate Chip Cookies"
        assert recipe.source_url == "https://www.youtube.com/watch?v=test123"
        assert recipe.source_platform == "youtube"
        assert recipe.servings == 24
        assert len(recipe.ingredients) == 4
        assert len(recipe.steps) == 4

    def test_list_recipes(self, test_db: Session, sample_recipe_json):
        """Test listing all recipes."""
        recipe_data = RecipeLLMOutput.model_validate(sample_recipe_json)

        # Create multiple recipes
        recipe1 = recipe_service.create_recipe(
            db=test_db,
            source_url="https://www.youtube.com/watch?v=test1",
            source_platform="youtube",
            data=recipe_data,
        )

        recipe2 = recipe_service.create_recipe(
            db=test_db,
            source_url="https://www.youtube.com/watch?v=test2",
            source_platform="youtube",
            data=recipe_data,
        )

        recipes = recipe_service.list_recipes(test_db)

        assert len(recipes) >= 2
        recipe_ids = [r.id for r in recipes]
        assert recipe1.id in recipe_ids
        assert recipe2.id in recipe_ids

    def test_get_recipe_by_id(self, test_db: Session, sample_recipe_json):
        """Test getting a recipe by ID."""
        recipe_data = RecipeLLMOutput.model_validate(sample_recipe_json)

        created = recipe_service.create_recipe(
            db=test_db,
            source_url="https://www.youtube.com/watch?v=test123",
            source_platform="youtube",
            data=recipe_data,
        )

        retrieved = recipe_service.get_recipe(test_db, created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Chocolate Chip Cookies"

    def test_get_recipe_not_found(self, test_db: Session):
        """Test getting a non-existent recipe."""
        result = recipe_service.get_recipe(test_db, "non-existent-id")
        assert result is None

