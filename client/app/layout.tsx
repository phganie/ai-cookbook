"use client";

import "./globals.css";
import type { ReactNode } from "react";
import { AuthProvider } from "./contexts/AuthContext";
import { Header } from "./components/Header";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <AuthProvider>
          <div className="mx-auto flex min-h-screen max-w-4xl flex-col px-4 py-6">
            <Header />
            <main className="flex-1 pb-8">{children}</main>
            <footer className="mt-6 border-t border-slate-800 pt-4 text-xs text-slate-500">
              CookClip MVP – for demo use only.
            </footer>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}


