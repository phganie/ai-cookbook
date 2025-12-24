"use client";

import { FormEvent, useState } from "react";

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

type ExtractedRecipe = {
  title: string;
  servings: number | null;
  ingredients: Ingredient[];
  steps: Step[];
  missing_info: string[];
  notes: string[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ExtractedRecipe | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);

  async function handleExtract(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setData(null);
    setSavedId(null);
    if (!url.trim()) {
      setError("Please paste a YouTube URL.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "Failed to extract recipe.");
      }
      const json = (await res.json()) as ExtractedRecipe;
      setData(json);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unexpected error extracting recipe."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!data) return;
    setSaveError(null);
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/recipes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_url: url,
          source_platform: "youtube",
          data
        })
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "Failed to save recipe.");
      }
      const json = await res.json();
      setSavedId(json.id);
    } catch (err) {
      setSaveError(
        err instanceof Error ? err.message : "Unexpected error saving recipe."
      );
    } finally {
      setSaving(false);
    }
  }

  function videoLinkFor(startSec: number) {
    try {
      const urlObj = new URL(url);
      if (urlObj.hostname.includes("youtu")) {
        if (urlObj.searchParams.has("v")) {
          urlObj.searchParams.set("t", `${Math.round(startSec)}`);
        } else {
          // short link: add ?t=
          urlObj.searchParams.set("t", `${Math.round(startSec)}`);
        }
        return urlObj.toString();
      }
    } catch {
      // ignore
    }
    return url;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg shadow-slate-950/40">
        <h2 className="mb-3 text-lg font-semibold text-slate-50">
          Paste a cooking video URL
        </h2>
        <p className="mb-4 text-sm text-slate-300">
          CookClip will pull the transcript, extract a structured recipe, and
          link each step back to the video so you can verify details instantly.
        </p>
        <form onSubmit={handleExtract} className="space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              className="flex-1 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-primary-light focus:outline-none focus:ring-1 focus:ring-primary-light"
            />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-white shadow-md shadow-primary/30 hover:bg-primary-light disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Extracting…" : "Extract Recipe"}
            </button>
          </div>
          {error && (
            <p className="text-sm text-rose-400" role="alert">
              {error}
            </p>
          )}
        </form>
      </section>

      {data && (
        <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-slate-50">
                {data.title}
              </h2>
              {data.servings != null && (
                <p className="mt-1 text-sm text-slate-300">
                  Servings:{" "}
                  <span className="font-medium text-slate-50">
                    {data.servings}
                  </span>
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center justify-center rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save to Library"}
            </button>
          </div>
          {saveError && (
            <p className="text-sm text-rose-400" role="alert">
              {saveError}
            </p>
          )}
          {savedId && (
            <p className="text-sm text-emerald-400">
              Saved! View it in your{" "}
              <a
                href={`/recipes/${savedId}`}
                className="underline decoration-emerald-400 underline-offset-2"
              >
                recipe page
              </a>{" "}
              or{" "}
              <a
                href="/library"
                className="underline decoration-emerald-400 underline-offset-2"
              >
                library
              </a>
              .
            </p>
          )}

          <div className="grid gap-6 md:grid-cols-[1.1fr,1.4fr]">
            <div>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-300">
                Ingredients
              </h3>
              <ul className="space-y-2 text-sm text-slate-100">
                {data.ingredients.map((ing, idx) => (
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
                Steps
              </h3>
              <ol className="space-y-2 text-sm text-slate-100">
                {data.steps.map((step) => (
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
                      {Math.round(step.start_sec)}s –{" "}
                      {Math.round(step.end_sec)}s · “
                      {step.evidence_quote}”
                    </p>
                  </li>
                ))}
              </ol>
            </div>
          </div>

          {(data.missing_info.length > 0 || data.notes.length > 0) && (
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {data.missing_info.length > 0 && (
                <div>
                  <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-400">
                    Missing or unclear
                  </h3>
                  <ul className="list-disc space-y-1 pl-5 text-xs text-amber-100">
                    {data.missing_info.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              {data.notes.length > 0 && (
                <div>
                  <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-300">
                    Notes
                  </h3>
                  <ul className="list-disc space-y-1 pl-5 text-xs text-slate-200">
                    {data.notes.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}


