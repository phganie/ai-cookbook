import asyncio
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .logging_config import setup_logging

logger = logging.getLogger(__name__)
from .models import Recipe, User
from .schemas import AskAIFromExtractRequest, AskAIRequest, AskAIResponse, ExtractRequest, ExtractResponse, RecipeCreateRequest, RecipeLLMOutput, RecipeResponse, VideoMetadata
from .schemas.auth import GoogleAuthRequest, Token, UserCreate, UserLogin, UserResponse
from .dependencies import get_current_user
from .services import users as user_service
from .services.ask_ai import answer_recipe_question
from .services.llm import call_llm_for_recipe, call_llm_for_recipe_from_metadata
from .services.transcript import get_transcript_with_fallback
from .services.video_metadata import get_video_metadata
from .services import recipes as recipe_service

setup_logging()
Base.metadata.create_all(bind=engine)

# Migrate existing database: add missing columns if they don't exist
def migrate_database():
    """Add missing columns to existing tables if they don't exist."""
    from sqlalchemy import inspect, text
    
    try:
        inspector = inspect(engine)
        
        # Migrate recipes table
        if 'recipes' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('recipes')]
            
            if 'user_id' not in columns:
                logger.info("Adding 'user_id' column to recipes table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipes ADD COLUMN user_id VARCHAR"))
                    conn.commit()
                logger.info("Successfully added 'user_id' column")
            
            if 'transcript' not in columns:
                logger.info("Adding 'transcript' column to recipes table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipes ADD COLUMN transcript TEXT"))
                    conn.commit()
                logger.info("Successfully added 'transcript' column")
            
            # Add other missing columns that might be needed
            if 'source_platform' not in columns:
                logger.info("Adding 'source_platform' column to recipes table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipes ADD COLUMN source_platform VARCHAR DEFAULT 'youtube'"))
                    conn.commit()
                logger.info("Successfully added 'source_platform' column")
            
            if 'servings' not in columns:
                logger.info("Adding 'servings' column to recipes table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipes ADD COLUMN servings INTEGER"))
                    conn.commit()
                logger.info("Successfully added 'servings' column")
            
            if 'missing_info' not in columns:
                logger.info("Adding 'missing_info' column to recipes table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipes ADD COLUMN missing_info TEXT DEFAULT '[]'"))
                    conn.commit()
                logger.info("Successfully added 'missing_info' column")
            
            if 'notes' not in columns:
                logger.info("Adding 'notes' column to recipes table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipes ADD COLUMN notes TEXT DEFAULT '[]'"))
                    conn.commit()
                logger.info("Successfully added 'notes' column")
            
            if 'created_at' not in columns:
                logger.info("Adding 'created_at' column to recipes table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE recipes ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"))
                    conn.commit()
                logger.info("Successfully added 'created_at' column")
        
        # Migrate users table
        if 'users' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'google_id' not in columns:
                logger.info("Adding 'google_id' column to users table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR"))
                    conn.commit()
                logger.info("Successfully added 'google_id' column")
            
            if 'auth_provider' not in columns:
                logger.info("Adding 'auth_provider' column to users table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN auth_provider VARCHAR NOT NULL DEFAULT 'email'"))
                    conn.commit()
                logger.info("Successfully added 'auth_provider' column")
            
            if 'created_at' not in columns:
                logger.info("Adding 'created_at' column to users table...")
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"))
                    conn.commit()
                logger.info("Successfully added 'created_at' column")
            
            # Make hashed_password nullable if it's not already
            # SQLite doesn't support ALTER COLUMN, so we skip this check
            # The model already has nullable=True, so new users will work fine
    except Exception as e:
        logger.warning("Migration check failed (this is OK for new databases): %s", e)

migrate_database()

app = FastAPI(title="CookClip API")


@app.on_event("startup")
async def startup_event():
    """Clear caches on startup and pre-initialize services."""
    from app.config import get_settings
    from app.services.llm import initialize_vertex_ai
    
    # Clear caches to ensure fresh load from .env
    get_settings.cache_clear()
    initialize_vertex_ai.cache_clear()
    
    # Log what value is actually loaded
    settings = get_settings()
    logger.info("Server startup: VERTEX_PROJECT_ID=%s", settings.vertex_project_id)
    
    # Pre-initialize Vertex AI to avoid first-request delay
    try:
        initialize_vertex_ai()
        logger.info("Vertex AI pre-initialized successfully")
    except Exception as e:
        logger.warning("Failed to pre-initialize Vertex AI: %s", e)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ai-cookbook-ans-projects-1058c0be.vercel.app",
        "https://ai-cookbook-two.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/extract", response_model=ExtractResponse)
async def extract_recipe(payload: ExtractRequest):
    """
    Extract recipe from YouTube video with parallel processing.
    Video metadata is fetched in parallel with transcript extraction.
    """
    loop = asyncio.get_event_loop()
    
    # Start video metadata fetch in parallel (non-blocking)
    # run_in_executor returns a Future which we can await directly
    metadata_future = loop.run_in_executor(None, get_video_metadata, payload.url)
    
    # Get transcript (or metadata fallback)
    transcript_text = None
    source = None
    
    try:
        # Get transcript (this is the main bottleneck)
        # New fallback order: yt-dlp captions → youtube-transcript-api → metadata → audio (if enabled)
        transcript_text, _segments, source = await loop.run_in_executor(
            None,
            get_transcript_with_fallback,
            payload.url
        )
        logger.info("Transcript source: %s", source)
    except ValueError as exc:
        error_msg = str(exc)
        if "NO_TRANSCRIPT_AVAILABLE" in error_msg:
            # All transcript methods failed, try metadata fallback
            logger.info("No transcript available, attempting metadata-based recipe generation")
            metadata_for_fallback = await metadata_future
            if not metadata_for_fallback or not metadata_for_fallback.title:
                raise HTTPException(
                    status_code=400, 
                    detail="Could not extract transcript or fetch video metadata. Please ensure the video is accessible and has a title."
                ) from exc
            # Continue to metadata-based generation below
            source = "metadata"
            transcript_text = None  # Will use metadata instead
        else:
            raise HTTPException(status_code=400, detail=error_msg) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error getting transcript")
        # Try metadata fallback as last resort
        try:
            metadata_for_fallback = await metadata_future
            if metadata_for_fallback and metadata_for_fallback.title:
                logger.info("Falling back to metadata after unexpected error")
                source = "metadata"
                transcript_text = None
            else:
                raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(exc)}") from exc
        except Exception as metadata_exc:
            raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(exc)}") from exc

    # Extract recipe from transcript or metadata
    try:
        if source == "metadata":
            # Use metadata-based recipe generation
            # Get metadata (should already be fetched, but ensure we have it)
            metadata_for_fallback = await metadata_future
            if not metadata_for_fallback or not metadata_for_fallback.title:
                raise HTTPException(status_code=400, detail="Could not fetch video metadata for recipe generation")
            
            recipe = await loop.run_in_executor(
                None,
                call_llm_for_recipe_from_metadata,
                metadata_for_fallback.title,
                metadata_for_fallback.description,
            )
            logger.info("Generated recipe from video metadata (title: %s)", metadata_for_fallback.title)
        else:
            # Use transcript-based recipe extraction
            recipe = await loop.run_in_executor(
                None,
                call_llm_for_recipe,
                transcript_text
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to extract/generate recipe")
        raise HTTPException(status_code=500, detail=f"Failed to extract recipe: {str(exc)}") from exc

    # Wait for video metadata (should be done by now if it was fast)
    video_metadata = None
    try:
        metadata = await metadata_future
        if metadata:
            video_metadata = VideoMetadata(
                video_id=metadata.video_id,
                title=metadata.title,
                thumbnail_url=metadata.thumbnail_url,
                author=metadata.author,
                upload_date=metadata.upload_date,
                duration=metadata.duration,
            )
    except Exception as exc:
        logger.warning("Failed to fetch video metadata: %s", exc)
        # Don't fail the request if metadata fetch fails

    return ExtractResponse(
        recipe=recipe, 
        video_metadata=video_metadata, 
        transcript=transcript_text if source != "metadata" else None,
        transcript_source=source
    )


# Authentication endpoints
@app.post("/api/auth/signup", response_model=Token)
def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """Create a new user account."""
    # Check if user already exists
    existing_user = user_service.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    user = user_service.create_user(db, user_data.email, user_data.password)
    
    # Generate access token
    from .services.auth import create_access_token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
        ),
    )


@app.post("/api/auth/token", response_model=Token)
def login_for_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 compatible token endpoint (form data)."""
    user = user_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    from .services.auth import create_access_token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
        ),
    )


@app.post("/api/auth/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    """Login and get access token (JSON body)."""
    user = user_service.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    from .services.auth import create_access_token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
        ),
    )


@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        auth_provider=current_user.auth_provider,
        created_at=current_user.created_at,
    )


@app.post("/api/auth/google", response_model=Token)
def google_auth(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db),
):
    """Authenticate with Google OAuth using authorization code."""
    from .services.google_auth import exchange_code_for_token
    
    # Exchange authorization code for user info
    google_user_info = exchange_code_for_token(payload.code)
    if not google_user_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid Google authorization code"
        )
    
    email = google_user_info.get('email')
    google_id = google_user_info.get('sub')
    
    if not email or not google_id:
        raise HTTPException(
            status_code=400,
            detail="Missing email or Google ID in token"
        )
    
    # Get or create user
    user = user_service.get_or_create_google_user(db, email, google_id)
    
    # Generate access token
    from .services.auth import create_access_token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
        ),
    )


@app.get("/api/auth/google/url")
def get_google_auth_url():
    """Get Google OAuth authorization URL."""
    from .config import get_settings
    
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_redirect_uri:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured"
        )
    
    # Build Google OAuth URL
    import urllib.parse
    
    params = {
        'client_id': settings.google_oauth_client_id,
        'redirect_uri': settings.google_oauth_redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent',
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    
    return {"auth_url": auth_url}


@app.post("/api/recipes", response_model=RecipeResponse)
def save_recipe(
    payload: RecipeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = recipe_service.create_recipe(
        db=db,
        user_id=current_user.id,
        source_url=payload.source_url,
        source_platform=payload.source_platform,
        data=payload.data,
        transcript=payload.transcript,
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
        transcript=recipe.transcript,
    )


@app.get("/api/recipes", response_model=list[RecipeResponse])
def list_recipes_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipes = recipe_service.list_recipes(db, user_id=current_user.id)
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
            transcript=r.transcript,
        )
        for r in recipes
    ]


@app.get("/api/recipes/{recipe_id}", response_model=RecipeResponse)
def get_recipe_endpoint(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe: Recipe | None = recipe_service.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this recipe")

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
        transcript=recipe.transcript,
    )


@app.delete("/api/recipes/{recipe_id}")
def delete_recipe_endpoint(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a recipe by ID."""
    recipe = recipe_service.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this recipe")
    
    deleted = recipe_service.delete_recipe(db, recipe_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"message": "Recipe deleted successfully"}


@app.get("/api/recipes/by-url")
def find_recipe_by_url_endpoint(
    source_url: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Find a recipe by source URL. Returns recipe ID if found, null otherwise."""
    recipe = recipe_service.find_recipe_by_url(db, source_url, user_id=current_user.id)
    if not recipe:
        return {"id": None}
    return {"id": recipe.id}

@app.post("/api/extract/ask", response_model=AskAIResponse)
async def ask_ai_about_extracted_recipe(payload: AskAIFromExtractRequest):
    """
    Answer questions about an extracted recipe (before saving to library).
    This allows users to ask questions immediately after extraction.
    """
    try:
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            answer_recipe_question,
            payload.question,
            payload.recipe,
            payload.transcript,
        )
        return AskAIResponse(answer=answer)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to answer question for extracted recipe")
        raise HTTPException(status_code=500, detail="Failed to answer question") from exc


@app.post("/api/recipes/{recipe_id}/ask", response_model=AskAIResponse)
async def ask_ai_about_recipe(
    recipe_id: str,
    payload: AskAIRequest,
    db: Session = Depends(get_db),
):
    """
    Answer questions about a saved recipe using the transcript and recipe data.
    """
    # Get recipe
    recipe = recipe_service.get_recipe(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Convert recipe to RecipeLLMOutput for the ask_ai service
    from .schemas import Ingredient, Step, RecipeLLMOutput
    
    recipe_data = RecipeLLMOutput(
        title=recipe.title,
        servings=recipe.servings,
        ingredients=[Ingredient.model_validate(ing) for ing in recipe.ingredients],
        steps=[Step.model_validate(step) for step in recipe.steps],
        missing_info=recipe.missing_info,
        notes=recipe.notes,
    )
    
    # Answer the question
    try:
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            answer_recipe_question,
            payload.question,
            recipe_data,
            recipe.transcript,
        )
        return AskAIResponse(answer=answer)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to answer question for recipe %s", recipe_id)
        raise HTTPException(status_code=500, detail="Failed to answer question") from exc


@app.get("/health")
def health():
    return {"ok": True}