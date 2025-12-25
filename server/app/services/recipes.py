from sqlalchemy.orm import Session

from .. import models
from ..schemas import RecipeLLMOutput


def create_recipe(
    db: Session,
    user_id: str,
    source_url: str,
    source_platform: str,
    data: RecipeLLMOutput,
    transcript: str | None = None,
) -> models.Recipe:
    recipe = models.Recipe(
        user_id=user_id,
        source_url=source_url,
        source_platform=source_platform,
        title=data.title,
        servings=data.servings,
        ingredients=[i.model_dump() for i in data.ingredients],
        steps=[s.model_dump() for s in data.steps],
        missing_info=data.missing_info,
        notes=data.notes,
        transcript=transcript,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def list_recipes(db: Session, user_id: str) -> list[models.Recipe]:
    return db.query(models.Recipe).filter(models.Recipe.user_id == user_id).order_by(models.Recipe.created_at.desc()).all()


def get_recipe(db: Session, recipe_id: str) -> models.Recipe | None:
    return db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()


def delete_recipe(db: Session, recipe_id: str) -> bool:
    """Delete a recipe by ID. Returns True if deleted, False if not found."""
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not recipe:
        return False
    db.delete(recipe)
    db.commit()
    return True


def find_recipe_by_url(db: Session, source_url: str, user_id: str) -> models.Recipe | None:
    """Find a recipe by source URL for a specific user. Useful for checking if a recipe is already saved."""
    return db.query(models.Recipe).filter(
        models.Recipe.source_url == source_url,
        models.Recipe.user_id == user_id
    ).first()


