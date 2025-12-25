"""
Main schemas for the CookClip API.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    start_sec: float
    end_sec: float
    quote: str = Field(max_length=200)

    @field_validator("start_sec", "end_sec", mode="before")
    @classmethod
    def coerce_time(cls, v):
        if v is None or v == "":
            return 0.0  # Default to 0 if None or empty
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0  # Default to 0 if conversion fails

    @field_validator("end_sec")
    @classmethod
    def end_after_start(cls, end, info):
        start = info.data.get("start_sec", 0.0)
        return end if end >= start else start


class Ingredient(BaseModel):
    name: str
    amount: Optional[float] = None
    unit: Optional[str] = None
    prep: Optional[str] = None
    source: Literal["explicit", "inferred"]
    evidence: Evidence
    # AI-suggested amounts when not specified in video
    suggested_amount: Optional[float] = None
    suggested_unit: Optional[str] = None


class Step(BaseModel):
    step_number: int
    text: str
    start_sec: float
    end_sec: float
    evidence_quote: str = Field(max_length=200)
    # AI-suggested step text when the original step is ambiguous or unclear
    suggested_text: Optional[str] = None

    @field_validator("start_sec", "end_sec", mode="before")
    @classmethod
    def coerce_time(cls, v):
        if v is None or v == "":
            return 0.0  # Default to 0 if None or empty
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0  # Default to 0 if conversion fails


class RecipeLLMOutput(BaseModel):
    title: str
    servings: Optional[int] = None
    ingredients: list[Ingredient]
    steps: list[Step]
    missing_info: list[str] = []
    notes: list[str] = []

    @field_validator("servings", mode="before")
    @classmethod
    def coerce_servings(cls, v):
        if v is None or v == "":
            return None
        try:
            return int(float(v))
        except Exception:
            return None

    @field_validator("ingredients")
    @classmethod
    def ensure_no_hallucinated_amounts(cls, v: list[Ingredient]) -> list[Ingredient]:
        for ing in v:
            # If inferred has amount/unit, move them to suggested_amount/unit
            if ing.source == "inferred" and (ing.amount is not None or ing.unit is not None):
                # Auto-fix: move amount/unit to suggested_amount/unit
                if ing.suggested_amount is None:
                    ing.suggested_amount = ing.amount
                if ing.suggested_unit is None:
                    ing.suggested_unit = ing.unit
                # Clear the amount/unit since it's inferred
                ing.amount = None
                ing.unit = None

            # explicit with no amount+unit -> downgrade (e.g., "salt to taste")
            if ing.source == "explicit" and (ing.amount is None and ing.unit is None):
                ing.source = "inferred"
        return v


class VideoMetadata(BaseModel):
    """Video metadata from YouTube."""
    video_id: str
    title: str
    thumbnail_url: str
    author: str
    upload_date: Optional[str] = None
    duration: Optional[int] = None


class ExtractRequest(BaseModel):
    url: str


class ExtractResponse(BaseModel):
    """Response from /api/extract including recipe and video metadata."""
    recipe: RecipeLLMOutput
    video_metadata: Optional[VideoMetadata] = None
    transcript: Optional[str] = None  # Include transcript for Ask AI feature
    transcript_source: Optional[str] = None  # "captions", "audio", or "metadata"


class RecipeCreateRequest(BaseModel):
    source_url: str
    source_platform: str = "youtube"
    data: RecipeLLMOutput
    transcript: Optional[str] = None  # Optional transcript for Ask AI


class RecipeResponse(BaseModel):
    id: str
    source_url: str
    source_platform: str
    title: str
    servings: Optional[int]
    ingredients: list[Ingredient]
    steps: list[Step]
    missing_info: list[str]
    notes: list[str]
    transcript: Optional[str] = None  # Include transcript for Ask AI


class AskAIRequest(BaseModel):
    """Request for asking questions about a recipe."""
    recipe_id: str | None = None  # Optional for extract endpoint
    question: str


class AskAIFromExtractRequest(BaseModel):
    """Request for asking questions about an extracted recipe (before saving)."""
    recipe: RecipeLLMOutput
    transcript: str | None = None
    question: str


class AskAIResponse(BaseModel):
    """Response from Ask AI endpoint."""
    answer: str
