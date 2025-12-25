"use client";

import { Suspense } from "react";
import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "../../../contexts/AuthContext";

function CallbackClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { googleAuth } = useAuth();

  useEffect(() => {
    const code = searchParams.get("code");
    const error = searchParams.get("error");

    if (error) {
      router.push(`/auth/login?error=${encodeURIComponent(error)}`);
      return;
    }

    if (!code) {
      router.push("/auth/login?error=no_code");
      return;
    }

    googleAuth(code)
      .then(() => {
        router.push("/library");
      })
      .catch((err) => {
        router.push(`/auth/login?error=${encodeURIComponent(err.message)}`);
      });
  }, [searchParams, googleAuth, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-slate-300">Completing Google sign in...</p>
    </div>
  );
}

export const dynamic = "force-dynamic";

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-slate-300">Completing Google sign in...</p>
        </div>
      }
    >
      <CallbackClient />
    </Suspense>
  );
}