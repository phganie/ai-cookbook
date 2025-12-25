"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ExtractResponse, RecipeLLMOutput } from "@shared/types";
import { API_BASE_URL } from "@shared/config";
import { LoadingProgress } from "./components/LoadingProgress";
import { AskAI } from "./components/AskAI";
import { useAuth } from "./contexts/AuthContext";

const API_BASE = API_BASE_URL;

export default function HomePage() {
  const { token, isAuthenticated } = useAuth();
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RecipeLLMOutput | null>(null);
  const [videoMetadata, setVideoMetadata] = useState<ExtractResponse["video_metadata"]>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [transcriptSource, setTranscriptSource] = useState<string | null>(null);
  const [checkedIngredients, setCheckedIngredients] = useState<Set<number>>(new Set());
  const [checkedSteps, setCheckedSteps] = useState<Set<number>>(new Set());
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);

  async function handleExtract(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setData(null);
    setVideoMetadata(null);
    setTranscript(null);
    setTranscriptSource(null);
    setSavedId(null);
    setCheckedIngredients(new Set());
    setCheckedSteps(new Set());
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
      const json = (await res.json()) as ExtractResponse;
      setData(json.recipe);
      setVideoMetadata(json.video_metadata);
      setTranscript(json.transcript);
      setTranscriptSource(json.transcript_source);
      // Reset checkboxes
      setCheckedIngredients(new Set());
      setCheckedSteps(new Set());
      
      // Check if recipe is already saved (only if authenticated)
      if (isAuthenticated && token) {
        try {
          const checkRes = await fetch(`${API_BASE}/api/recipes/by-url?source_url=${encodeURIComponent(url)}`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (checkRes.ok) {
            const checkJson = await checkRes.json();
            if (checkJson.id) {
              setSavedId(checkJson.id);
            }
          }
        } catch {
          // Ignore errors when checking
        }
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unexpected error extracting recipe."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveToggle() {
    if (!data) return;
    
    // Require authentication
    if (!isAuthenticated || !token) {
      router.push("/auth/login");
      return;
    }
    
    setSaveError(null);
    
    // If already saved, unsave it
    if (savedId) {
      setSaving(true);
      try {
        const res = await fetch(`${API_BASE}/api/recipes/${savedId}`, {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail ?? "Failed to unsave recipe.");
        }
        setSavedId(null);
      } catch (err) {
        setSaveError(
          err instanceof Error ? err.message : "Unexpected error unsaving recipe."
        );
      } finally {
        setSaving(false);
      }
      return;
    }
    
    // Otherwise, save it
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/recipes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          source_url: url,
          source_platform: "youtube",
          data,
          transcript
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

      {loading && <LoadingProgress isVisible={loading} />}

          {data && (
            <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              {/* Transcript Source Warning */}
              {transcriptSource === "metadata" && (
                <div className="rounded-lg border border-amber-700 bg-amber-900/30 p-3">
                  <p className="text-sm text-amber-200">
                    <span className="font-semibold">Note:</span> This video doesn't have a transcript available. 
                    We've generated a recipe based on the video title and description using AI. 
                    All ingredients and steps are AI-suggested and may not match the exact recipe in the video.
                  </p>
                </div>
              )}
              
              {/* Video Metadata */}
              {videoMetadata && (
            <div className="flex gap-4 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
              {videoMetadata.thumbnail_url && (
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="shrink-0"
                >
                  <img
                    src={videoMetadata.thumbnail_url}
                    alt={videoMetadata.title}
                    className="h-24 w-40 rounded-md object-cover"
                  />
                </a>
              )}
              <div className="flex-1 space-y-1">
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-sm font-medium text-primary-light hover:underline"
                >
                  {videoMetadata.title}
                </a>
                <p className="text-xs text-slate-400">
                  by <span className="text-slate-300">{videoMetadata.author}</span>
                  {videoMetadata.upload_date && (
                    <> · {videoMetadata.upload_date}</>
                  )}
                </p>
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block text-xs text-slate-500 hover:text-primary-light"
                >
                  Watch on YouTube →
                </a>
              </div>
            </div>
          )}

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
            <div className="flex items-center gap-2">
              <AskAI recipe={data} transcript={transcript} />
              <button
                type="button"
                onClick={handleSaveToggle}
                disabled={saving}
                className="inline-flex items-center justify-center rounded-md p-2 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-600/20 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
                aria-label={savedId ? "Remove from library" : "Save to library"}
                title={savedId ? "Remove from library" : "Save to library"}
              >
                {saving ? (
                  <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : savedId ? (
                  <svg className="h-5 w-5 fill-emerald-400" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                  </svg>
                )}
              </button>
            </div>
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
                Steps
              </h3>
              <ol className="space-y-2 text-sm text-slate-100">
                {data.steps.map((step) => (
                  <li
                    key={step.step_number}
                    className={`rounded-md bg-slate-900/80 px-3 py-2 transition-opacity ${
                      checkedSteps.has(step.step_number) ? "opacity-60" : ""
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2 flex-1">
                        <input
                          type="checkbox"
                          checked={checkedSteps.has(step.step_number)}
                          onChange={(e) => {
                            const newChecked = new Set(checkedSteps);
                            if (e.target.checked) {
                              newChecked.add(step.step_number);
                            } else {
                              newChecked.delete(step.step_number);
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
                            <span className={checkedSteps.has(step.step_number) ? "line-through" : ""}>
                              {step.text}
                            </span>
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
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {data.missing_info.length > 0 && (
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
                    {data.missing_info.map((item) => (
                      <li key={item} className="flex items-start gap-2 text-sm text-amber-100">
                        <span className="text-amber-400 mt-1">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {data.notes.length > 0 && (
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
                    {data.notes.map((item) => (
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
        </section>
      )}
    </div>
  );
}


