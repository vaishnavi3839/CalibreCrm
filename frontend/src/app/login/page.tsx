"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/Brand";
import { api } from "@/lib/api";
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

/** OAuth Web client IDs are public; fallback keeps Sign-In working if env was missing at build. */
const FALLBACK_GOOGLE_CLIENT_ID =
  "113963656390-odafike631l3st0onl83t4181b0vj75m.apps.googleusercontent.com";

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleClientId, setGoogleClientId] = useState(
    () => process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || FALLBACK_GOOGLE_CLIENT_ID
  );
  const googleBtnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api<{ google_client_id?: string | null }>(
          "/api/v1/auth/public-config",
          { method: "GET" },
          false
        );
        const fromApi = res.data?.google_client_id?.trim();
        if (!cancelled && fromApi) setGoogleClientId(fromApi);
      } catch {
        // Keep env / fallback client id
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!googleClientId) return;

    const scriptId = "google-gsi";
    const existing = document.getElementById(scriptId);
    const init = () => {
      if (!window.google || !googleBtnRef.current) return;
      window.google.accounts.id.initialize({
        client_id: googleClientId,
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
  }, [googleClientId, loginWithGoogle, router]);

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

          {googleClientId ? (
            <div className="flex justify-center">
              <div ref={googleBtnRef} />
            </div>
          ) : (
            <p className="text-center text-sm text-red-600">
              Google Sign-In is not configured. Set GOOGLE_CLIENT_ID on the API.
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
