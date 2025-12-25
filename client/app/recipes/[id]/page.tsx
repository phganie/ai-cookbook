"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Recipe } from "@shared/types";
import { API_BASE_URL } from "@shared/config";
import { AskAI } from "../../components/AskAI";
import { useAuth } from "../../contexts/AuthContext";

const API_BASE = API_BASE_URL;

export default function RecipePage({
  params
}: {
  params: { id: string };
}) {
  const { id } = params;
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkedIngredients, setCheckedIngredients] = useState<Set<number>>(new Set());
  const [checkedSteps, setCheckedSteps] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (authLoading) return;
    
    if (!isAuthenticated || !token) {
      router.push("/auth/login");
      return;
    }

    async function load() {
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/api/recipes/${id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail ?? "Failed to load recipe.");
        }
        const json = (await res.json()) as Recipe;
        setRecipe(json);
        // Reset checkboxes when recipe loads
        setCheckedIngredients(new Set());
        setCheckedSteps(new Set());
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Unexpected error loading recipe."
        );
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [id, isAuthenticated, token, authLoading, router]);

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
        <AskAI recipeId={recipe.id} />
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
                className={`flex items-start justify-between gap-2 rounded-md bg-slate-900/80 px-3 py-2 transition-opacity ${
                  checkedIngredients.has(idx) ? "opacity-60" : ""
                }`}
              >
                <div className="flex items-start gap-2 flex-1">
                  <input
                    type="checkbox"
                    checked={checkedIngredients.has(idx)}
                    onChange={(e) => {
                      const newChecked = new Set(checkedIngredients);
                      if (e.target.checked) {
                        newChecked.add(idx);
                      } else {
                        newChecked.delete(idx);
                      }
                      setCheckedIngredients(newChecked);
                    }}
                    className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-800 text-primary focus:ring-primary"
                  />
                  <div className="flex-1">
                      <div className={`font-medium ${checkedIngredients.has(idx) ? "line-through" : ""}`}>
                        {ing.name}
                      </div>
                      <div className="text-xs text-slate-400">
                        {ing.amount != null && ing.unit ? (
                          `${ing.amount} ${ing.unit}`
                        ) : (
                          <>
                            Amount not specified
                            {ing.suggested_amount != null && ing.suggested_unit ? (
                              <div className="mt-0.5 text-amber-400">
                                ~{ing.suggested_amount} {ing.suggested_unit} (AI-suggested)
                              </div>
                            ) : null}
                          </>
                        )}
                        {ing.prep ? ` · ${ing.prep}` : ""}
                      </div>
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
            {recipe.steps.map((step, idx) => (
              <li
                key={step.step_number}
                className={`rounded-md bg-slate-900/80 px-3 py-2 transition-opacity ${
                  checkedSteps.has(idx) ? "opacity-60" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2 flex-1">
                    <input
                      type="checkbox"
                      checked={checkedSteps.has(idx)}
                      onChange={(e) => {
                        const newChecked = new Set(checkedSteps);
                        if (e.target.checked) {
                          newChecked.add(idx);
                        } else {
                          newChecked.delete(idx);
                        }
                        setCheckedSteps(newChecked);
                      }}
                      className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-800 text-primary focus:ring-primary"
                    />
                    <div className="flex-1">
                      <span className="mr-2 text-xs font-semibold text-slate-400">
                        {step.step_number}.
                      </span>
                      <div>
                        <span className={checkedSteps.has(idx) ? "line-through" : ""}>{step.text}</span>
                        {step.suggested_text && (
                          <div className="mt-1 text-xs text-amber-400">
                            AI-suggested: {step.suggested_text}
                          </div>
                        )}
                      </div>
                    </div>
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
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {recipe.missing_info.length > 0 && (
            <div className="rounded-lg border border-amber-800/50 bg-amber-950/30 p-4">
              <div className="flex items-center gap-2 mb-3">
                <svg className="h-5 w-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <h3 className="text-sm font-semibold text-amber-300">
                  Missing or Unclear Information
                </h3>
              </div>
              <ul className="space-y-2">
                {recipe.missing_info.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-sm text-amber-100">
                    <span className="text-amber-400 mt-1">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {recipe.notes.length > 0 && (
            <div className="rounded-lg border border-blue-800/50 bg-blue-950/30 p-4">
              <div className="flex items-center gap-2 mb-3">
                <svg className="h-5 w-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <h3 className="text-sm font-semibold text-blue-300">
                  Tips & Notes
                </h3>
              </div>
              <ul className="space-y-2">
                {recipe.notes.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-sm text-blue-100">
                    <span className="text-blue-400 mt-1">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}


