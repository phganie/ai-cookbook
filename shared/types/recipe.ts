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
};

export type Step = {
  step_number: number;
  text: string;
  start_sec: number;
  end_sec: number;
  evidence_quote: string;
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

export type RecipeCreateRequest = {
  source_url: string;
  source_platform: string;
  data: RecipeLLMOutput;
};

