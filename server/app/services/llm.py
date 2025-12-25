import json
import logging
from functools import lru_cache

from ..config import get_settings
from ..schemas import RecipeLLMOutput

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """
You are a meticulous recipe extraction assistant.
Given a transcript of a cooking video, you MUST return ONLY JSON following EXACTLY this schema:

{ ...same schema... }

CRITICAL FIELD NAMES (use exactly these):
- "title" (NOT "recipe_name", "name", or "recipe")
- "name" for ingredient name (NOT "item", "ingredient", or "ingredient_name")
- "text" for step text (NOT "instruction", "step", "description", or "action")
- "start_sec" and "end_sec" must be numbers (NOT null, use 0.0 if unknown)

Rules:
- NEVER hallucinate precise quantities or units. If the creator does NOT explicitly say an amount or unit, set amount=null and unit=null and set source="inferred".
- If the creator explicitly says an amount (e.g., "2 cups of flour"), set source="explicit".
- For ingredients where amount=null (not specified in video), provide suggested_amount and suggested_unit based on typical recipe amounts for that ingredient. These are AI suggestions to help users, not from the video.
- suggested_amount and suggested_unit should be reasonable defaults (e.g., "salt" → 1 tsp, "onion" → 1 medium, "white wine" → 0.5 cup, "bacon" → 4 slices).
- If amount is specified (not null), you may still provide suggested_amount/suggested_unit if helpful, but they should match the actual amount.
- evidence_quote must be a short excerpt (<= 20 words) from the transcript.
- steps must be concise imperative sentences ("Chop the onions", "Preheat the oven to 180C").
- Timestamps (start_sec, end_sec) are REQUIRED numbers. Use 0.0 if timestamp cannot be determined from transcript.
- If any important information is missing or unclear, add a short description to missing_info.

Return ONLY the JSON object, no explanation.
"""

METADATA_SYSTEM_PROMPT = """
You are a helpful recipe generation assistant.
Given a video title and description (but no transcript), generate a reasonable recipe for this dish.
You MUST return ONLY JSON following EXACTLY this schema:

{
  "title": string,
  "servings": number|null,
  "ingredients": [
    {
      "name": string,
      "amount": number|null,
      "unit": string|null,
      "prep": string|null,
      "source": "inferred",
      "evidence": { "start_sec": 0.0, "end_sec": 0.0, "quote": string },
      "suggested_amount": number|null,
      "suggested_unit": string|null
    }
  ],
  "steps": [
    {
      "step_number": number,
      "text": string,
      "start_sec": 0.0,
      "end_sec": 0.0,
      "evidence_quote": string,
      "suggested_text": string|null
    }
  ],
  "missing_info": [string],
  "notes": [string]
}

CRITICAL FIELD NAMES (use exactly these):
- "title" (NOT "recipe_name", "name", or "recipe")
- "name" for ingredient name (NOT "item", "ingredient", or "ingredient_name")
- "text" for step text (NOT "instruction", "step", "description", or "action")

Rules:
- Since there is no transcript, ALL ingredients should have source="inferred" and amount=null, unit=null.
- Provide suggested_amount and suggested_unit for all ingredients based on standard recipe amounts for this dish.
- evidence.start_sec and evidence.end_sec should be 0.0 (no timestamps available).
- evidence.quote should be a brief description like "Based on dish name" or similar.
- steps should have start_sec=0.0 and end_sec=0.0 (no timestamps).
- steps.evidence_quote should indicate it's inferred (e.g., "Based on standard recipe for [dish name]").
- Generate reasonable steps based on typical cooking methods for this type of dish.
- If steps are ambiguous or missing details, provide suggested_text with clearer instructions.
- Add any assumptions or missing information to missing_info (e.g., "Cooking temperature not specified", "Exact timing inferred from standard practice").

Return ONLY the JSON object, no explanation.
"""

def build_user_prompt(transcript: str) -> str:
    # More concise prompt to reduce token count
    return f"Extract recipe from transcript:\n\n{transcript}"


def build_metadata_prompt(title: str, description: str | None = None) -> str:
    """Build prompt for generating recipe from video metadata (title/description)."""
    context = f"Video title: {title}"
    if description:
        # Truncate description to first 500 chars to avoid token limits
        desc = description[:500] + ("..." if len(description) > 500 else "")
        context += f"\n\nVideo description: {desc}"
    
    return f"""Generate a recipe based on the video title and description below.
Since there is no transcript available, create a reasonable recipe structure for this dish.
Use standard cooking practices and typical ingredient amounts for this type of recipe.

{context}

Generate a complete recipe with ingredients and steps based on the dish name and any available description."""


@lru_cache
def initialize_vertex_ai() -> None:
    """Initialize Vertex AI with project and location."""
    # Lazy import to avoid import errors during testing
    from google.cloud import aiplatform
    
    settings = get_settings()
    if not settings.vertex_project_id:
        raise RuntimeError("VERTEX_PROJECT_ID is not set")
    
    logger.info("Initializing Vertex AI with project=%s, location=%s", 
                settings.vertex_project_id, settings.vertex_location)
    
    aiplatform.init(
        project=settings.vertex_project_id,
        location=settings.vertex_location or "us-central1",
    )


@lru_cache(maxsize=2)
def _get_model_instance(model_name: str):
    """Cache model instances to avoid recreating them on every call."""
    from vertexai.generative_models import GenerativeModel
    return GenerativeModel(model_name=model_name)


def _clean_model_text(text: str) -> str:
    import re
    text = (text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Try to fix common JSON issues first
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Remove comments (JSON doesn't support comments)
    text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    
    # Extract JSON object more intelligently
    # Find the first opening brace
    start = text.find("{")
    if start == -1:
        return text.strip()
    
    # Find matching closing brace by counting braces
    brace_count = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i
                break
    
    if brace_count == 0 and end > start:
        text = text[start : end + 1]
    else:
        # Fallback: use rfind if brace matching fails
        end = text.rfind("}")
        if end > start:
            text = text[start : end + 1]
    
    return text.strip()


def _normalize_llm_output(raw_json: dict) -> dict:
    """
    Normalize LLM output to match our schema.
    Handles common field name variations from the LLM and provides defaults for missing fields.
    """
    normalized = raw_json.copy()
    
    # Normalize top-level fields
    if "recipe_name" in normalized and "title" not in normalized:
        normalized["title"] = normalized.pop("recipe_name")
    
    # Ensure required fields have defaults
    if "title" not in normalized:
        normalized["title"] = "Untitled Recipe"
    if "ingredients" not in normalized:
        normalized["ingredients"] = []
    if "steps" not in normalized:
        normalized["steps"] = []
    if "missing_info" not in normalized:
        normalized["missing_info"] = []
    if "notes" not in normalized:
        normalized["notes"] = []
    
    # Normalize ingredients
    if "ingredients" in normalized:
        for ing in normalized["ingredients"]:
            if "item" in ing and "name" not in ing:
                ing["name"] = ing.pop("item")
            # Ensure evidence exists and has timestamps
            if "evidence" not in ing:
                ing["evidence"] = {"start_sec": 0.0, "end_sec": 0.0, "quote": ""}
            else:
                if ing["evidence"].get("start_sec") is None:
                    ing["evidence"]["start_sec"] = 0.0
                if ing["evidence"].get("end_sec") is None:
                    ing["evidence"]["end_sec"] = ing["evidence"].get("start_sec", 0.0) + 1.0
                if "quote" not in ing["evidence"]:
                    ing["evidence"]["quote"] = ""
            # Ensure timestamps are not None
            if ing.get("start_sec") is None:
                ing["start_sec"] = 0.0
            if ing.get("end_sec") is None:
                ing["end_sec"] = 0.0
    
    # Normalize steps
    if "steps" in normalized:
        for step in normalized["steps"]:
            if "instruction" in step and "text" not in step:
                step["text"] = step.pop("instruction")
            if "step" in step and "text" not in step:
                step["text"] = step.pop("step")
            # Ensure timestamps are not None
            if step.get("start_sec") is None:
                step["start_sec"] = 0.0
            if step.get("end_sec") is None:
                step["end_sec"] = step.get("start_sec", 0.0) + 1.0
            # Ensure evidence_quote exists
            if "evidence_quote" not in step and "quote" in step:
                step["evidence_quote"] = step.pop("quote")
            elif "evidence_quote" not in step:
                step["evidence_quote"] = step.get("text", "")[:200]
            # Ensure step_number exists
            if "step_number" not in step:
                step["step_number"] = normalized["steps"].index(step) + 1
    
    return normalized


def call_llm_for_recipe(
    transcript_text: str,
    model: str | None = None,
    max_retries: int = 2,  # Reduced from 3 to 2 for faster failure
) -> RecipeLLMOutput:
    settings = get_settings()
    initialize_vertex_ai()

    model_name = (model or settings.vertex_model).lower()
    
    # Log the actual model name being used
    logger.info("Using Vertex AI model: %s (from settings: %s)", model_name, settings.vertex_model)

    # Truncate very long transcripts to speed up processing (keep first 8000 chars)
    # This covers most recipes while significantly reducing token count
    if len(transcript_text) > 8000:
        logger.info("Truncating transcript from %d to 8000 chars for faster processing", len(transcript_text))
        transcript_text = transcript_text[:8000] + "\n[... transcript truncated for length ...]"

    # More concise prompt structure to reduce tokens
    full_prompt = f"{EXTRACTION_SYSTEM_PROMPT.strip()}\n\n{build_user_prompt(transcript_text)}"

    last_error: Exception | None = None

    # Get cached model instance
    model_instance = _get_model_instance(model_name)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Vertex Gemini extract attempt=%s model=%s", attempt, model_name)

            # Lazy import to avoid import errors during testing
            from vertexai.generative_models import GenerationConfig

            response = model_instance.generate_content(
                full_prompt,
                generation_config=GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    max_output_tokens=8192,  # Increased to handle longer recipes with many steps
                    top_p=0.95,  # Nucleus sampling for faster generation
                    top_k=40,  # Top-k sampling for faster generation
                ),
            )

            content = _clean_model_text(response.text)
            if not content:
                raise ValueError("Empty response from Vertex AI")

            # Log the cleaned content length for debugging
            logger.debug("Cleaned JSON content length: %d chars", len(content))
            
            # Try to parse JSON, with better error handling
            try:
                raw_json = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("JSON parse error at position %d: %s", e.pos, e.msg)
                logger.error("Content around error: %s", content[max(0, e.pos-50):e.pos+50])
                logger.error("Full content length: %d, Last 200 chars: %s", len(content), content[-200:])
                
                # Check if JSON appears truncated (common issue with LLM responses)
                open_braces = content.count('{')
                close_braces = content.count('}')
                open_brackets = content.count('[')
                close_brackets = content.count(']')
                
                if open_braces > close_braces or open_brackets > close_brackets:
                    logger.warning("JSON appears truncated: %d open braces, %d close braces", open_braces, close_braces)
                    # Try to complete the JSON by adding missing closing brackets
                    missing_braces = open_braces - close_braces
                    missing_brackets = open_brackets - close_brackets
                    
                    # Find the last array/object that needs closing
                    # Add closing brackets in reverse order
                    completion = ""
                    for _ in range(missing_brackets):
                        completion += "]"
                    for _ in range(missing_braces):
                        completion += "}"
                    
                    content = content + completion
                    logger.info("Attempting to complete JSON with: %s", completion)
                    
                    try:
                        raw_json = json.loads(content)
                        logger.info("Successfully parsed JSON after completion")
                    except json.JSONDecodeError as e2:
                        logger.error("Failed to parse JSON after completion: %s", e2.msg)
                        raise ValueError(f"Invalid/truncated JSON from LLM: {e.msg} at position {e.pos}") from e
                else:
                    # Try to fix other common issues
                    import re
                    content = re.sub(r',(\s*[}\]])', r'\1', content)
                    try:
                        raw_json = json.loads(content)
                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON after cleanup. First 500 chars: %s", content[:500])
                        raise ValueError(f"Invalid JSON from LLM: {e.msg} at position {e.pos}") from e
            
            # Normalize field names and handle None values
            normalized_json = _normalize_llm_output(raw_json)
            return RecipeLLMOutput.model_validate(normalized_json)

        except Exception as exc:
            logger.exception("Vertex extraction attempt=%s failed: %s", attempt, exc)
            last_error = exc

    raise RuntimeError(f"Failed to extract recipe after {max_retries} attempts: {last_error}")


def call_llm_for_recipe_from_metadata(
    title: str,
    description: str | None = None,
    model: str | None = None,
    max_retries: int = 2,
) -> RecipeLLMOutput:
    """Generate recipe from video title/description using LLM when no transcript is available."""
    settings = get_settings()
    initialize_vertex_ai()

    model_name = (model or settings.vertex_model).lower()
    
    logger.info("Using Vertex AI model: %s for metadata-based recipe generation", model_name)

    # Build prompt from metadata
    full_prompt = f"{METADATA_SYSTEM_PROMPT.strip()}\n\n{build_metadata_prompt(title, description)}"

    last_error: Exception | None = None

    # Get cached model instance
    model_instance = _get_model_instance(model_name)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Vertex Gemini metadata recipe generation attempt=%s model=%s", attempt, model_name)

            from vertexai.generative_models import GenerationConfig

            response = model_instance.generate_content(
                full_prompt,
                generation_config=GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    max_output_tokens=8192,
                    top_p=0.95,
                    top_k=40,
                ),
            )

            content = _clean_model_text(response.text)
            if not content:
                raise ValueError("Empty response from Vertex AI")

            logger.debug("Cleaned JSON content length: %d chars", len(content))
            
            try:
                raw_json = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("JSON parse error at position %d: %s", e.pos, e.msg)
                logger.error("Content around error: %s", content[max(0, e.pos-50):e.pos+50])
                
                # Check if JSON appears truncated
                open_braces = content.count('{')
                close_braces = content.count('}')
                open_brackets = content.count('[')
                close_brackets = content.count(']')
                
                if open_braces > close_braces or open_brackets > close_brackets:
                    logger.warning("JSON appears truncated: %d open braces, %d close braces", open_braces, close_braces)
                    missing_braces = open_braces - close_braces
                    missing_brackets = open_brackets - close_brackets
                    
                    completion = ""
                    for _ in range(missing_brackets):
                        completion += "]"
                    for _ in range(missing_braces):
                        completion += "}"
                    
                    content = content + completion
                    logger.info("Attempting to complete JSON with: %s", completion)
                    
                    try:
                        raw_json = json.loads(content)
                        logger.info("Successfully parsed JSON after completion")
                    except json.JSONDecodeError as e2:
                        logger.error("Failed to parse JSON after completion: %s", e2.msg)
                        raise ValueError(f"Invalid/truncated JSON from LLM: {e.msg} at position {e.pos}") from e
                else:
                    import re
                    content = re.sub(r',(\s*[}\]])', r'\1', content)
                    try:
                        raw_json = json.loads(content)
                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON after cleanup. First 500 chars: %s", content[:500])
                        raise ValueError(f"Invalid JSON from LLM: {e.msg} at position {e.pos}") from e
            
            # Normalize field names and handle None values
            normalized_json = _normalize_llm_output(raw_json)
            return RecipeLLMOutput.model_validate(normalized_json)

        except Exception as exc:
            logger.exception("Vertex metadata recipe generation attempt=%s failed: %s", attempt, exc)
            last_error = exc

    raise RuntimeError(f"Failed to generate recipe from metadata after {max_retries} attempts: {last_error}")