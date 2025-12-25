"use client";

import Link from "next/link";
import { useAuth } from "../contexts/AuthContext";
import { useRouter } from "next/navigation";

export function Header() {
  const { user, logout, isAuthenticated } = useAuth();
  const router = useRouter();

  function handleLogout() {
    logout();
    router.push("/");
  }

  return (
    <header className="mb-6 flex items-center justify-between">
      <h1 className="text-2xl font-semibold tracking-tight">
        <Link href="/" className="flex items-center">
          <span className="rounded-md bg-primary/20 px-2 py-1 text-primary-light">
            CookClip
          </span>
          <span className="ml-2 text-sm text-slate-300">
            Video to recipe you can actually follow
          </span>
        </Link>
      </h1>
      <nav className="flex items-center gap-4 text-sm text-slate-300">
        <Link href="/" className="hover:text-primary-light">
          Home
        </Link>
        {isAuthenticated && (
          <Link href="/library" className="hover:text-primary-light">
            Library
          </Link>
        )}
        {isAuthenticated ? (
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link
              href="/auth/login"
              className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
            >
              Login
            </Link>
            <Link
              href="/auth/signup"
              className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-light transition-colors"
            >
              Sign Up
            </Link>
          </div>
        )}
      </nav>
    </header>
  );
}

