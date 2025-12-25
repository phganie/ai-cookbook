"""
Service for answering questions about recipes using the transcript and LLM.
"""
import logging
from functools import lru_cache

from ..config import get_settings
from ..schemas import RecipeLLMOutput

logger = logging.getLogger(__name__)


def answer_recipe_question(
    question: str,
    recipe: RecipeLLMOutput,
    transcript: str | None = None,
    model: str | None = None,
) -> str:
    """
    Answer a question about a recipe using the transcript and extracted recipe data.
    
    Args:
        question: User's question
        recipe: The extracted recipe data
        transcript: The original video transcript (optional but recommended)
        model: Vertex AI model to use (optional)
    
    Returns:
        Answer string from the LLM
    """
    from ..services.llm import initialize_vertex_ai
    
    settings = get_settings()
    initialize_vertex_ai()
    
    model_name = (model or settings.vertex_model).lower()
    logger.info("Answering question with model: %s", model_name)
    
    # Truncate very long transcripts to speed up processing (keep first 4000 chars)
    # This is usually enough context for answering questions
    if transcript and len(transcript) > 4000:
        logger.info("Truncating transcript from %d to 4000 chars for faster processing", len(transcript))
        transcript = transcript[:4000] + "\n[... transcript truncated ...]"
    
    # Build context from recipe
    ingredients_list = []
    for ing in recipe.ingredients:
        if ing.amount and ing.unit:
            ingredients_list.append(f"- {ing.name}: {ing.amount} {ing.unit}")
        elif ing.suggested_amount and ing.suggested_unit:
            ingredients_list.append(f"- {ing.name}: ~{ing.suggested_amount} {ing.suggested_unit} (AI-suggested)")
        else:
            ingredients_list.append(f"- {ing.name}: (amount not specified)")
        if ing.prep:
            ingredients_list[-1] += f", {ing.prep}"
    
    recipe_summary = f"""
Recipe: {recipe.title}
Servings: {recipe.servings if recipe.servings else 'Not specified'}

Ingredients:
{chr(10).join(ingredients_list)}

Steps:
{chr(10).join(f"{step.step_number}. {step.text}" for step in recipe.steps)}
"""
    
    # Build concise prompt to reduce token count
    system_prompt = """You are a cooking assistant. Answer the user's question using ONLY the provided Recipe data and Transcript as sources.

Rules:
1) If the answer is explicitly supported by Recipe or Transcript, say so and cite where:
   - Use citations like: [Recipe: Ingredients], [Recipe: Step 3], [Transcript].
2) If the answer is NOT supported, say "Not specified in the recipe/transcript" and give a best-practice suggestion.
   - Do NOT claim the recipe/transcript says something it doesn't.
3) Be practical and concise. Prefer concrete numbers when giving suggestions (temps, times, ratios), and include safe ranges when uncertain.
4) If the user asks for substitutions, dietary changes, scaling, or troubleshooting, give 2–4 options with tradeoffs.
5) Output format:
   - Source: Recipe | Transcript | Suggestion
   - Answer: (2–6 sentences or bullets)
"""
    
    transcript_section = f"\n\nTranscript:\n{transcript}" if transcript else ""
    user_prompt = f"""Context:
[Recipe]
Title: {recipe.title}
Servings: {recipe.servings if recipe.servings else "Not specified"}

Ingredients:
{chr(10).join(ingredients_list)}

Steps:
{chr(10).join(f"{step.step_number}. {step.text}" for step in recipe.steps)}

{f"[Transcript]\\n{transcript}" if transcript else ""}

Question: {question}
"""
    
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    try:
        from vertexai.generative_models import GenerationConfig
        from ..services.llm import _get_model_instance
        
        # Reuse cached model instance
        model_instance = _get_model_instance(model_name)
        
        response = model_instance.generate_content(
            full_prompt,
            generation_config=GenerationConfig(
                temperature=0.3,  # Slightly higher for more natural answers
                max_output_tokens=500,  # Limit response length for faster generation
                top_p=0.95,  # Nucleus sampling for faster generation
                top_k=40,  # Top-k sampling for faster generation
            ),
        )
        
        answer = (response.text or "").strip()
        if not answer:
            return "I couldn't generate an answer. Please try rephrasing your question."
        
        return answer
        
    except Exception as exc:
        logger.exception("Failed to answer question: %s", exc)
        raise RuntimeError(f"Failed to answer question: {exc}") from exc

