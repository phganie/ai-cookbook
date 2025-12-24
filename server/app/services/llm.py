import json
import logging
from typing import Any, Dict

from openai import OpenAI

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


def get_openai_client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=settings.openai_api_key)


def call_llm_for_recipe(
    transcript_text: str,
    model: str = "gpt-4o-mini",
    max_retries: int = 3,
) -> RecipeLLMOutput:
    client = get_openai_client()
    system_prompt = EXTRACTION_SYSTEM_PROMPT.strip()
    user_prompt = build_user_prompt(transcript_text)

    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Calling LLM for recipe extraction attempt=%s", attempt)

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")

            raw_json = json.loads(content)
            parsed = RecipeLLMOutput.model_validate(raw_json)
            return parsed
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error during LLM extraction attempt=%s: %s", attempt, exc)
            last_error = exc

    raise RuntimeError(f"Failed to extract recipe after {max_retries} attempts: {last_error}")  # type: ignore[arg-type]


