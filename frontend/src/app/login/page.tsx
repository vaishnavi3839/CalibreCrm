"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/Brand";
import { dashboardPathForRole, useAuth } from "@/lib/auth-context";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void;
          renderButton: (el: HTMLElement, config: Record<string, unknown>) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const googleBtnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    const scriptId = "google-gsi";
    const existing = document.getElementById(scriptId);
    const init = () => {
      if (!window.google || !googleBtnRef.current) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response: { credential: string }) => {
          setBusy(true);
          setError("");
          try {
            const user = await loginWithGoogle(response.credential);
            router.replace(dashboardPathForRole(user.role.name));
          } catch (err) {
            setError(err instanceof Error ? err.message : "Google sign-in failed");
          } finally {
            setBusy(false);
          }
        },
      });
      googleBtnRef.current.innerHTML = "";
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: "outline",
        size: "large",
        width: 360,
        text: "signin_with",
        shape: "pill",
      });
    };

    if (existing) {
      init();
      return;
    }
    const script = document.createElement("script");
    script.id = scriptId;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = init;
    document.body.appendChild(script);
  }, [loginWithGoogle, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await login(email, password);
      router.replace(dashboardPathForRole(user.role.name));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="aviation-grid relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(47,127,184,0.28),transparent_40%),radial-gradient(circle_at_80%_10%,rgba(196,163,90,0.22),transparent_35%)]" />
      <div className="pointer-events-none absolute -left-24 top-24 h-72 w-72 rounded-full bg-sky-400/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-16 bottom-10 h-80 w-80 rounded-full bg-brass-500/10 blur-3xl" />

      <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col justify-center gap-10 px-4 py-10 lg:flex-row lg:items-center lg:gap-20">
        <div className="animate-rise flex max-w-xl flex-col items-center text-center lg:items-start lg:text-left">
          <BrandLogo className="h-44 w-auto drop-shadow-xl sm:h-56" priority />
          <div className="mt-5 text-xs uppercase tracking-[0.28em] text-brass-500">Keep Climbing</div>
          <h1 className="mt-3 font-[family-name:var(--font-display)] text-4xl leading-tight text-navy-900 sm:text-5xl">
            Calibre Aviation Academy
          </h1>
        </div>

        <form
          onSubmit={onSubmit}
          className="glass-panel animate-rise-delay-1 w-full max-w-md rounded-3xl p-6 sm:p-8"
        >
          <h2 className="text-xl font-semibold text-navy-900">Sign in</h2>
          <p className="mt-1 text-sm text-muted">Use your academy email — only accounts added by Admin can sign in</p>

          <label className="mt-6 block text-sm font-medium text-navy-800">
            Email
            <input
              className="mt-1.5 w-full rounded-xl border border-cloud-200 bg-white px-3 py-2.5 outline-none ring-sky-400 focus:ring-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
              autoComplete="username"
            />
          </label>
          <label className="mt-4 block text-sm font-medium text-navy-800">
            Password
            <input
              className="mt-1.5 w-full rounded-xl border border-cloud-200 bg-white px-3 py-2.5 outline-none ring-sky-400 focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
              autoComplete="current-password"
            />
          </label>

          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

          <button
            disabled={busy}
            className="mt-6 w-full rounded-xl px-4 py-3 text-sm font-semibold transition disabled:opacity-60"
            style={{ color: "#fff", backgroundColor: "#0a1628" }}
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>

          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-cloud-200" />
            <span className="text-xs uppercase tracking-wider text-muted">or</span>
            <div className="h-px flex-1 bg-cloud-200" />
          </div>

          {GOOGLE_CLIENT_ID ? (
            <div className="flex justify-center">
              <div ref={googleBtnRef} />
            </div>
          ) : (
            <button
              type="button"
              onClick={() =>
                setError(
                  "Google Sign-In is not configured yet. Set NEXT_PUBLIC_GOOGLE_CLIENT_ID (and GOOGLE_CLIENT_ID on the API) from Google Cloud Console."
                )
              }
              className="flex w-full items-center justify-center gap-3 rounded-xl border border-cloud-200 bg-white px-4 py-3 text-sm font-semibold text-navy-900 hover:bg-cloud-50"
            >
              <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
                <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.9 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.5-.4-3.5z" />
                <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 12 24 12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.3 4 24 4 16.1 4 9.2 8.5 6.3 14.7z" />
                <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.3 35.1 26.8 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.1 39.4 16 44 24 44z" />
                <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-1.1 3.2-3.5 5.8-6.5 7.3l.1.1 6.2 5.2C36.9 39.2 44 34 44 24c0-1.3-.1-2.5-.4-3.5z" />
              </svg>
              Sign in with Google
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
