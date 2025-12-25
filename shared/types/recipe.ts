/**
 * Shared TypeScript types for CookClip recipe domain
 * These types match the backend Pydantic schemas in server/app/schemas.py
 */

export type Evidence = {
  start_sec: number;
  end_sec: number;
  quote: string;
};

export type Ingredient = {
  name: string;
  amount: number | null;
  unit: string | null;
  prep: string | null;
  source: "explicit" | "inferred";
  evidence: Evidence;
  suggested_amount: number | null;
  suggested_unit: string | null;
};

export type Step = {
  step_number: number;
  text: string;
  start_sec: number;
  end_sec: number;
  evidence_quote: string;
  suggested_text: string | null; // AI-suggested step text when ambiguous
};

export type RecipeLLMOutput = {
  title: string;
  servings: number | null;
  ingredients: Ingredient[];
  steps: Step[];
  missing_info: string[];
  notes: string[];
};

export type Recipe = {
  id: string;
  source_url: string;
  source_platform: string;
  title: string;
  servings: number | null;
  ingredients: Ingredient[];
  steps: Step[];
  missing_info: string[];
  notes: string[];
  transcript: string | null;
};

export type RecipeListItem = {
  id: string;
  title: string;
  source_url: string;
  servings: number | null;
};

// API Request/Response types
export type ExtractRequest = {
  url: string;
};

export type VideoMetadata = {
  video_id: string;
  title: string;
  thumbnail_url: string;
  author: string;
  upload_date: string | null;
  duration: number | null;
};

export type ExtractResponse = {
  recipe: RecipeLLMOutput;
  video_metadata: VideoMetadata | null;
  transcript: string | null;
  transcript_source: string | null; // "captions", "audio", or "metadata"
};

export type AskAIRequest = {
  recipe_id: string | null;
  question: string;
};

export type AskAIFromExtractRequest = {
  recipe: RecipeLLMOutput;
  transcript: string | null;
  question: string;
};

export type AskAIResponse = {
  answer: string;
};

export type RecipeCreateRequest = {
  source_url: string;
  source_platform: string;
  data: RecipeLLMOutput;
  transcript: string | null;
};

