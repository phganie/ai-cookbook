from sqlalchemy.orm import Session

from .. import models
from ..schemas import RecipeLLMOutput


def create_recipe(
    db: Session,
    source_url: str,
    source_platform: str,
    data: RecipeLLMOutput,
) -> models.Recipe:
    recipe = models.Recipe(
        source_url=source_url,
        source_platform=source_platform,
        title=data.title,
        servings=data.servings,
        ingredients=[i.model_dump() for i in data.ingredients],
        steps=[s.model_dump() for s in data.steps],
        missing_info=data.missing_info,
        notes=data.notes,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def list_recipes(db: Session) -> list[models.Recipe]:
    return db.query(models.Recipe).order_by(models.Recipe.created_at.desc()).all()


def get_recipe(db: Session, recipe_id: str) -> models.Recipe | None:
    return db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()


