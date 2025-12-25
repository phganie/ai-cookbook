from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    start_sec: float
    end_sec: float
    quote: str = Field(max_length=200)

    @field_validator("start_sec", "end_sec", mode="before")
    @classmethod
    def coerce_time(cls, v):
        return float(v)

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
            # inferred must NOT have amount/unit
            if ing.source == "inferred" and (ing.amount is not None or ing.unit is not None):
                raise ValueError(f"Inferred ingredient has amount/unit: {ing.name}")

            # explicit with no amount+unit -> downgrade (e.g., "salt to taste")
            if ing.source == "explicit" and (ing.amount is None and ing.unit is None):
                ing.source = "inferred"
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