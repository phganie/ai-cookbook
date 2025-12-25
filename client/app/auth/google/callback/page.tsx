import { Suspense } from "react";
import CallbackClient from "./CallbackClient";

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