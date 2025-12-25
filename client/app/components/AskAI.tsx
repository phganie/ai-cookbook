"use client";

import { FormEvent, useEffect, useState } from "react";
import { AskAIFromExtractRequest, AskAIResponse, RecipeLLMOutput } from "@shared/types";
import { API_BASE_URL } from "@shared/config";
import { useAuth } from "../contexts/AuthContext";

const API_BASE = API_BASE_URL;

interface AskAIProps {
  recipeId?: string;  // Optional: for saved recipes
  recipe?: RecipeLLMOutput;  // Optional: for extracted recipes (before saving)
  transcript?: string | null;  // Optional: transcript for extracted recipes
}

export function AskAI({ recipeId, recipe, transcript }: AskAIProps) {
  const { token } = useAuth();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showChat, setShowChat] = useState(false);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (showChat) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [showChat]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;

    setError(null);
    setAnswer(null);
    setLoading(true);

    try {
      let res: Response;
      
      const headers: HeadersInit = { "Content-Type": "application/json" };
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      if (recipeId) {
        // Saved recipe: use recipe ID endpoint
        res = await fetch(`${API_BASE}/api/recipes/${recipeId}/ask`, {
          method: "POST",
          headers,
          body: JSON.stringify({ recipe_id: recipeId, question: question.trim() }),
        });
      } else if (recipe) {
        // Extracted recipe: use extract/ask endpoint
        res = await fetch(`${API_BASE}/api/extract/ask`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            recipe,
            transcript: transcript || null,
            question: question.trim(),
          } as AskAIFromExtractRequest),
        });
      } else {
        throw new Error("No recipe data available");
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? "Failed to get answer.");
      }

      const json = (await res.json()) as AskAIResponse;
      setAnswer(json.answer);
      setQuestion(""); // Clear question after successful answer
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setShowChat(true)}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-white shadow-md shadow-primary/30 hover:bg-primary-light transition-colors"
        aria-label="Ask AI"
      >
        <svg
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
        Ask AI
      </button>

      {showChat && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowChat(false);
              setQuestion("");
              setAnswer(null);
              setError(null);
            }
          }}
        >
          <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
            {/* Header */}
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-700 bg-slate-900 px-6 py-4">
              <h3 className="text-xl font-semibold text-slate-50">Ask AI</h3>
              <button
                onClick={() => {
                  setShowChat(false);
                  setQuestion("");
                  setAnswer(null);
                  setError(null);
                }}
                className="text-slate-400 hover:text-slate-200 transition-colors rounded-md p-1 hover:bg-slate-800"
                aria-label="Close"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-4">
              <p className="text-sm text-slate-400">
                Ask questions about this recipe. The AI has access to the full video transcript and recipe data.
              </p>

              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="e.g., What temperature should I cook this at?"
                    className="flex-1 rounded-md border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-primary-light focus:outline-none focus:ring-2 focus:ring-primary-light"
                    disabled={loading}
                    autoFocus
                  />
                  <button
                    type="submit"
                    disabled={loading || !question.trim()}
                    className="inline-flex items-center justify-center rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-white shadow-md shadow-primary/30 hover:bg-primary-light disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
                  >
                    {loading ? (
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : (
                      "Ask"
                    )}
                  </button>
                </div>
              </form>

              {error && (
                <div className="rounded-md bg-rose-900/30 border border-rose-800 px-4 py-3 text-sm text-rose-300">
                  {error}
                </div>
              )}

              {answer && (
                <div className="rounded-md bg-slate-800/80 border border-slate-700 px-4 py-4">
                  <div className="flex items-start gap-3">
                    <svg className="h-5 w-5 text-primary shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm text-slate-200 whitespace-pre-wrap flex-1">{answer}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

