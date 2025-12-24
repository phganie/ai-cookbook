from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    start_sec: float
    end_sec: float
    quote: str = Field(max_length=200)


class Ingredient(BaseModel):
    name: str
    amount: Optional[float] = None
    unit: Optional[str] = None
    prep: Optional[str] = None
    source: Literal["explicit", "inferred"]
    evidence: Evidence


class Step(BaseModel):
    step_number: int
    text: str
    start_sec: float
    end_sec: float
    evidence_quote: str = Field(max_length=200)


class RecipeLLMOutput(BaseModel):
    title: str
    servings: Optional[int] = None
    ingredients: list[Ingredient]
    steps: list[Step]
    missing_info: list[str]
    notes: list[str]

    @field_validator("ingredients")
    @classmethod
    def ensure_no_hallucinated_amounts(cls, v: list[Ingredient]) -> list[Ingredient]:
        # This is mostly enforced by prompt; here we just keep hook for possible checks.
        return v


class ExtractRequest(BaseModel):
    url: str


class RecipeCreateRequest(BaseModel):
    source_url: str
    source_platform: str = "youtube"
    data: RecipeLLMOutput


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


