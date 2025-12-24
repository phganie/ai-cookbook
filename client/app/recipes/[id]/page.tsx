"use client";

import { useEffect, useState } from "react";

type Ingredient = {
  name: string;
  amount: number | null;
  unit: string | null;
  prep: string | null;
  source: "explicit" | "inferred";
  evidence: { start_sec: number; end_sec: number; quote: string };
};

type Step = {
  step_number: number;
  text: string;
  start_sec: number;
  end_sec: number;
  evidence_quote: string;
};

type Recipe = {
  id: string;
  title: string;
  servings: number | null;
  source_url: string;
  source_platform: string;
  ingredients: Ingredient[];
  steps: Step[];
  missing_info: string[];
  notes: string[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function RecipePage({
  params
}: {
  params: { id: string };
}) {
  const { id } = params;
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/api/recipes/${id}`);
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail ?? "Failed to load recipe.");
        }
        const json = (await res.json()) as Recipe;
        setRecipe(json);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Unexpected error loading recipe."
        );
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [id]);

  function videoLinkFor(startSec: number) {
    if (!recipe) return "#";
    try {
      const urlObj = new URL(recipe.source_url);
      if (urlObj.hostname.includes("youtu")) {
        urlObj.searchParams.set("t", `${Math.round(startSec)}`);
        return urlObj.toString();
      }
    } catch {
      // ignore
    }
    return recipe?.source_url ?? "#";
  }

  if (loading) {
    return <p className="text-sm text-slate-300">Loading recipe…</p>;
  }

  if (error) {
    return (
      <p className="text-sm text-rose-400" role="alert">
        {error}
      </p>
    );
  }

  if (!recipe) {
    return (
      <p className="text-sm text-slate-300">
        Recipe not found. Go back to your{" "}
        <a href="/library" className="text-primary-light underline">
          library
        </a>
        .
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-50">
            {recipe.title}
          </h2>
          <p className="mt-1 text-sm text-slate-300">
            From{" "}
            <a
              href={recipe.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-primary-light underline"
            >
              original video
            </a>
            {recipe.servings != null && (
              <>
                {" "}
                · Servings:{" "}
                <span className="font-medium text-slate-50">
                  {recipe.servings}
                </span>
              </>
            )}
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-[1.05fr,1.5fr]">
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-300">
            Ingredients
          </h3>
          <ul className="space-y-2 text-sm text-slate-100">
            {recipe.ingredients.map((ing, idx) => (
              <li
                key={`${ing.name}-${idx}`}
                className="flex items-start justify-between gap-2 rounded-md bg-slate-900/80 px-3 py-2"
              >
                <div>
                  <div className="font-medium">{ing.name}</div>
                  <div className="text-xs text-slate-400">
                    {ing.amount != null && ing.unit
                      ? `${ing.amount} ${ing.unit}`
                      : "Amount not specified"}
                    {ing.prep ? ` · ${ing.prep}` : ""}
                  </div>
                </div>
                <div className="shrink-0 text-[10px] uppercase tracking-wide text-slate-500">
                  {ing.source === "explicit" ? "Explicit" : "Inferred"}
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-300">
            Cook mode
          </h3>
          <ol className="space-y-2 text-sm text-slate-100">
            {recipe.steps.map((step) => (
              <li
                key={step.step_number}
                className="rounded-md bg-slate-900/80 px-3 py-2"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="mr-2 text-xs font-semibold text-slate-400">
                      {step.step_number}.
                    </span>
                    <span>{step.text}</span>
                  </div>
                  <a
                    href={videoLinkFor(step.start_sec)}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 text-xs text-primary-light hover:underline"
                  >
                    Jump to video
                  </a>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {Math.round(step.start_sec)}s – {Math.round(step.end_sec)}s ·
                  “{step.evidence_quote}”
                </p>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {(recipe.missing_info.length > 0 || recipe.notes.length > 0) && (
        <div className="grid gap-4 md:grid-cols-2">
          {recipe.missing_info.length > 0 && (
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-400">
                Missing or unclear
              </h3>
              <ul className="list-disc space-y-1 pl-5 text-xs text-amber-100">
                {recipe.missing_info.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {recipe.notes.length > 0 && (
            <div>
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-300">
                Notes
              </h3>
              <ul className="list-disc space-y-1 pl-5 text-xs text-slate-200">
                {recipe.notes.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


