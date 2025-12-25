"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RecipeListItem } from "@shared/types";
import { API_BASE_URL } from "@shared/config";
import { useAuth } from "../contexts/AuthContext";

const API_BASE = API_BASE_URL;

export default function LibraryPage() {
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<RecipeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    
    if (!isAuthenticated || !token) {
      router.push("/auth/login");
      return;
    }

    async function load() {
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/api/recipes`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail ?? "Failed to load recipes.");
        }
        const json = await res.json();
        setItems(json);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Unexpected error loading recipes."
        );
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [isAuthenticated, token, authLoading, router]);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-slate-50">Your cookbook</h2>
      <p className="text-sm text-slate-300">
        Saved recipes extracted from your favorite cooking videos.
      </p>
      {loading && (
        <p className="text-sm text-slate-300">Loading your recipes…</p>
      )}
      {error && (
        <p className="text-sm text-rose-400" role="alert">
          {error}
        </p>
      )}
      {!loading && !error && items.length === 0 && (
        <p className="text-sm text-slate-400">
          You haven&apos;t saved any recipes yet. Extract one from the{" "}
          <a href="/" className="text-primary-light underline">
            home page
          </a>
          .
        </p>
      )}
      <ul className="space-y-2">
        {items.map((item) => (
          <li
            key={item.id}
            className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm"
          >
            <div>
              <a
                href={`/recipes/${item.id}`}
                className="font-medium text-slate-50 hover:text-primary-light"
              >
                {item.title}
              </a>
              <div className="mt-1 text-xs text-slate-400">
                {item.servings != null
                  ? `Servings: ${item.servings} · `
                  : ""}
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:underline"
                >
                  Original video
                </a>
              </div>
            </div>
            <a
              href={`/recipes/${item.id}`}
              className="text-xs text-primary-light hover:underline"
            >
              Open
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}


