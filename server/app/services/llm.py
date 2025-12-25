import json
import logging
from functools import lru_cache

from ..config import get_settings
from ..schemas import RecipeLLMOutput

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are a meticulous recipe extraction assistant.
Given a transcript of a cooking video, you MUST return ONLY JSON following EXACTLY this schema:

{
  "title": string,
  "servings": number|null,
  "ingredients": [
    {
      "name": string,
      "amount": number|null,
      "unit": string|null,
      "prep": string|null,
      "source": "explicit" | "inferred",
      "evidence": { "start_sec": number, "end_sec": number, "quote": string }
    }
  ],
  "steps": [
    {
      "step_number": number,
      "text": string,
      "start_sec": number,
      "end_sec": number,
      "evidence_quote": string
    }
  ],
  "missing_info": [string],
  "notes": [string]
}

Rules:
- NEVER hallucinate precise quantities or units. If the creator does NOT explicitly say an amount or unit, set amount=null and unit=null and set source="inferred".
- If the creator explicitly says an amount (e.g., "2 cups of flour"), set source="explicit".
- evidence_quote must be a short excerpt (<= 20 words) from the transcript.
- steps must be concise imperative sentences ("Chop the onions", "Preheat the oven to 180C").
- Timestamps should be in seconds from the start of the video.
- If any important information is missing or unclear, add a short description to missing_info.

Return ONLY the JSON object, no explanation.
"""


def build_user_prompt(transcript: str) -> str:
    return (
        "You are given a raw transcript of a cooking video.\n"
        "Build a structured recipe strictly following the JSON schema.\n\n"
        "TRANSCRIPT:\n"
        f"{transcript}"
    )


@lru_cache
def initialize_vertex_ai() -> None:
    """Initialize Vertex AI with project and location."""
    # Lazy import to avoid import errors during testing
    from google.cloud import aiplatform
    
    settings = get_settings()
    if not settings.vertex_project_id:
        raise RuntimeError("VERTEX_PROJECT_ID is not set")
    aiplatform.init(
        project=settings.vertex_project_id,
        location=settings.vertex_location or "us-central1",
    )


def _clean_model_text(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Fallback: extract first JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return text.strip()


def call_llm_for_recipe(
    transcript_text: str,
    model: str | None = None,
    max_retries: int = 3,
) -> RecipeLLMOutput:
    settings = get_settings()
    initialize_vertex_ai()

    model_name = model or settings.vertex_model

    full_prompt = (
        "SYSTEM INSTRUCTIONS:\n"
        f"{EXTRACTION_SYSTEM_PROMPT.strip()}\n\n"
        "USER REQUEST:\n"
        f"{build_user_prompt(transcript_text)}"
    )

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Vertex Gemini extract attempt=%s model=%s", attempt, model_name)

            # Lazy import to avoid import errors during testing
            from vertexai.generative_models import GenerativeModel, GenerationConfig

            model_instance = GenerativeModel(model_name=model_name)

            response = model_instance.generate_content(
                full_prompt,
                generation_config=GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            content = _clean_model_text(response.text)
            if not content:
                raise ValueError("Empty response from Vertex AI")

            raw_json = json.loads(content)
            return RecipeLLMOutput.model_validate(raw_json)

        except Exception as exc:
            logger.exception("Vertex extraction attempt=%s failed: %s", attempt, exc)
            last_error = exc

    raise RuntimeError(f"Failed to extract recipe after {max_retries} attempts: {last_error}")