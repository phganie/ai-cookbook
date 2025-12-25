"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "../../../contexts/AuthContext";

export default function CallbackClient() {
  const searchParams = useSearchParams();
  const { googleAuth } = useAuth();

  useEffect(() => {
    const code = searchParams.get("code");
    const error = searchParams.get("error");

    if (error) {
      window.opener?.postMessage(
        { type: "GOOGLE_OAUTH_ERROR", error },
        window.location.origin
      );
      window.close();
      return;
    }

    if (!code) {
      window.opener?.postMessage(
        { type: "GOOGLE_OAUTH_ERROR", error: "No authorization code received" },
        window.location.origin
      );
      window.close();
      return;
    }

    googleAuth(code)
      .then(() => {
        window.opener?.postMessage(
          { type: "GOOGLE_OAUTH_SUCCESS" },
          window.location.origin
        );
        window.close();
      })
      .catch((err) => {
        window.opener?.postMessage(
          { type: "GOOGLE_OAUTH_ERROR", error: err.message },
          window.location.origin
        );
        window.close();
      });
  }, [searchParams, googleAuth]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-slate-300">Completing Google sign in...</p>
    </div>
  );
}