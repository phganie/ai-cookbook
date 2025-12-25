"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "../../../contexts/AuthContext";
export const dynamic = "force-dynamic";


export default function GoogleCallbackPage() {
  const searchParams = useSearchParams();
  const { googleAuth } = useAuth();

  useEffect(() => {
    const code = searchParams.get("code");
    const error = searchParams.get("error");

    if (error) {
      // Send error to parent window
      if (window.opener) {
        window.opener.postMessage(
          { type: "GOOGLE_OAUTH_ERROR", error: error },
          window.location.origin
        );
      }
      window.close();
      return;
    }

    if (code) {
      // Authenticate with the code
      googleAuth(code)
        .then(() => {
          // Send success to parent window
          if (window.opener) {
            window.opener.postMessage(
              { type: "GOOGLE_OAUTH_SUCCESS" },
              window.location.origin
            );
          }
          window.close();
        })
        .catch((err) => {
          // Send error to parent window
          if (window.opener) {
            window.opener.postMessage(
              { type: "GOOGLE_OAUTH_ERROR", error: err.message },
              window.location.origin
            );
          }
          window.close();
        });
    } else {
      // No code, send error
      if (window.opener) {
        window.opener.postMessage(
          { type: "GOOGLE_OAUTH_ERROR", error: "No authorization code received" },
          window.location.origin
        );
      }
      window.close();
    }
  }, [searchParams, googleAuth]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <p className="text-slate-300">Completing Google sign in...</p>
      </div>
    </div>
  );
}

