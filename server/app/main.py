from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .logging_config import setup_logging
from .models import Recipe
from .schemas import ExtractRequest, RecipeCreateRequest, RecipeLLMOutput, RecipeResponse
from .services.llm import call_llm_for_recipe
from .services.youtube import get_youtube_transcript
from .services import recipes as recipe_service

setup_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CookClip API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/extract", response_model=RecipeLLMOutput)
def extract_recipe(payload: ExtractRequest):
    try:
        transcript_text, _segments = get_youtube_transcript(payload.url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        recipe = call_llm_for_recipe(transcript_text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to extract recipe") from exc

    return recipe


@app.post("/api/recipes", response_model=RecipeResponse)
def save_recipe(
    payload: RecipeCreateRequest,
    db: Session = Depends(get_db),
):
    recipe = recipe_service.create_recipe(
        db=db,
        source_url=payload.source_url,
        source_platform=payload.source_platform,
        data=payload.data,
    )
    return RecipeResponse(
        id=recipe.id,
        source_url=recipe.source_url,
        source_platform=recipe.source_platform,
        title=recipe.title,
        servings=recipe.servings,
        ingredients=recipe.ingredients,
        steps=recipe.steps,
        missing_info=recipe.missing_info,
        notes=recipe.notes,
    )


@app.get("/api/recipes", response_model=list[RecipeResponse])
def list_recipes_endpoint(db: Session = Depends(get_db)):
    recipes = recipe_service.list_recipes(db)
    return [
        RecipeResponse(
            id=r.id,
            source_url=r.source_url,
            source_platform=r.source_platform,
            title=r.title,
            servings=r.servings,
            ingredients=r.ingredients,
            steps=r.steps,
            missing_info=r.missing_info,
            notes=r.notes,
        )
        for r in recipes
    ]


@app.get("/api/recipes/{recipe_id}", response_model=RecipeResponse)
def get_recipe_endpoint(recipe_id: str, db: Session = Depends(get_db)):
    recipe: Recipe | None = recipe_service.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeResponse(
        id=recipe.id,
        source_url=recipe.source_url,
        source_platform=recipe.source_platform,
        title=recipe.title,
        servings=recipe.servings,
        ingredients=recipe.ingredients,
        steps=recipe.steps,
        missing_info=recipe.missing_info,
        notes=recipe.notes,
    )

@app.get("/health")
def health():
    return {"ok": True}