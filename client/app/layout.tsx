import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "CookClip",
  description: "Turn cooking videos into trustworthy, step-by-step recipes."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <div className="mx-auto flex min-h-screen max-w-4xl flex-col px-4 py-6">
          <header className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-semibold tracking-tight">
              <span className="rounded-md bg-primary/20 px-2 py-1 text-primary-light">
                CookClip
              </span>
              <span className="ml-2 text-sm text-slate-300">
                Video to recipe you can actually follow
              </span>
            </h1>
            <nav className="flex gap-3 text-sm text-slate-300">
              <a href="/" className="hover:text-primary-light">
                Home
              </a>
              <a href="/library" className="hover:text-primary-light">
                Library
              </a>
            </nav>
          </header>
          <main className="flex-1 pb-8">{children}</main>
          <footer className="mt-6 border-t border-slate-800 pt-4 text-xs text-slate-500">
            CookClip MVP – for demo use only.
          </footer>
        </div>
      </body>
    </html>
  );
}


