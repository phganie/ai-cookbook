import json
import logging
from typing import Any, Dict

from vertexai.generative_models import GenerativeModel
from google.cloud import aiplatform

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
        "You are given a raw transcript of a cooking video. "
        "Use it to build a structured recipe. Transcript:\n\n"
        f"{transcript}"
    )


def initialize_vertex_ai() -> None:
    """Initialize Vertex AI with project and location."""
    settings = get_settings()
    if not settings.vertex_project_id:
        raise RuntimeError("VERTEX_PROJECT_ID is not set")
    
    aiplatform.init(
        project=settings.vertex_project_id,
        location=settings.vertex_location or "us-central1",
    )


def call_llm_for_recipe(
    transcript_text: str,
    model: str | None = None,
    max_retries: int = 3,
) -> RecipeLLMOutput:
    """Call Vertex AI Gemini to extract recipe from transcript."""
    settings = get_settings()
    initialize_vertex_ai()
    
    # Use model from settings or parameter
    model_name = model or settings.vertex_model
    
    system_prompt = EXTRACTION_SYSTEM_PROMPT.strip()
    user_prompt = build_user_prompt(transcript_text)
    
    # Combine system and user prompts
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Calling Vertex AI Gemini for recipe extraction attempt=%s, model=%s", attempt, model_name)

            # Initialize the model with generation config for JSON output
            model_instance = GenerativeModel(
                model_name=model_name,
            )

            # Generate content with JSON response format
            response = model_instance.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )

            content = response.text
            if not content:
                raise ValueError("Empty response from Vertex AI")

            # Clean up the response (remove markdown code blocks if present)
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]  # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove closing ```
            content = content.strip()

            raw_json = json.loads(content)
            parsed = RecipeLLMOutput.model_validate(raw_json)
            return parsed
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error during Vertex AI extraction attempt=%s: %s", attempt, exc)
            last_error = exc

    raise RuntimeError(f"Failed to extract recipe after {max_retries} attempts: {last_error}")  # type: ignore[arg-type]


