"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BrandLogo } from "@/components/Brand";
import { api } from "@/lib/api";
import { dashboardPathForRole, useAuth } from "@/lib/auth-context";

declare global {
  interface Window {
    Capacitor?: {
      isNativePlatform?: () => boolean;
      getPlatform?: () => string;
    };
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void;
          renderButton: (el: HTMLElement, config: Record<string, unknown>) => void;
          prompt: (cb?: (notification: { isNotDisplayed: () => boolean; getNotDisplayedReason: () => string }) => void) => void;
        };
      };
    };
  }
}

/** OAuth Web client ID is public — always available even if Railway env was missing at build. */
export const GOOGLE_WEB_CLIENT_ID =
  "113963656390-odafike631l3st0onl83t4181b0vj75m.apps.googleusercontent.com";

function GoogleGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.4 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.5-.4-3.5z" />
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16.1 19 13 24 13c3 0 5.8 1.1 7.9 3l5.7-5.7C34.2 6.1 29.4 4 24 4 16.3 4 9.6 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.3 26.7 36 24 36c-5.3 0-9.7-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4.1 5.5l.1.1 6.2 5.2C39.2 36.3 44 31.5 44 24c0-1.3-.1-2.5-.4-3.5z" />
    </svg>
  );
}

function isNativeApp() {
  try {
    return Boolean(window.Capacitor?.isNativePlatform?.());
  } catch {
    return false;
  }
}

export function LoginClient() {
  const { login, loginWithGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleClientId, setGoogleClientId] = useState(GOOGLE_WEB_CLIENT_ID);
  const [googleReady, setGoogleReady] = useState(false);
  const [nativeMode, setNativeMode] = useState(false);
  const googleBtnRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const loginWithGoogleRef = useRef(loginWithGoogle);
  loginWithGoogleRef.current = loginWithGoogle;

  const handleCredential = useCallback(
    async (credential: string) => {
      setBusy(true);
      setError("");
      try {
        const user = await loginWithGoogleRef.current(credential);
        router.replace(dashboardPathForRole(user.role.name));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Google sign-in failed");
      } finally {
        setBusy(false);
      }
    },
    [router]
  );

  useEffect(() => {
    setNativeMode(isNativeApp());
  }, []);

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
        // Keep hardcoded client id
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Browser: load Google Identity Services button (blocked inside Capacitor WebView).
  useEffect(() => {
    if (!googleClientId || nativeMode) return;
    let cancelled = false;
    let tries = 0;
    let poll: number | undefined;

    const paintButton = () => {
      if (cancelled || !window.google || !googleBtnRef.current || !wrapRef.current) return false;
      const width = Math.max(240, Math.min(wrapRef.current.clientWidth || 320, 400));
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: (response: { credential: string }) => {
          void handleCredential(response.credential);
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      googleBtnRef.current.innerHTML = "";
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: "outline",
        size: "large",
        width,
        text: "signin_with",
        shape: "pill",
        logo_alignment: "left",
      });
      setGoogleReady(true);
      return true;
    };

    const scriptId = "google-gsi";
    let script = document.getElementById(scriptId) as HTMLScriptElement | null;
    if (!script) {
      script = document.createElement("script");
      script.id = scriptId;
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      document.body.appendChild(script);
    }
    script.addEventListener("load", () => {
      if (!cancelled) paintButton();
    });

    poll = window.setInterval(() => {
      tries += 1;
      if (window.google?.accounts?.id && paintButton()) {
        window.clearInterval(poll);
        return;
      }
      if (tries > 40) window.clearInterval(poll);
    }, 150);

    const onResize = () => {
      if (window.google?.accounts?.id) paintButton();
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelled = true;
      if (poll) window.clearInterval(poll);
      window.removeEventListener("resize", onResize);
    };
  }, [googleClientId, handleCredential, nativeMode]);

  // Native app: initialize Capgo Social Login (Google Credential Manager).
  useEffect(() => {
    if (!nativeMode || !googleClientId) return;
    let cancelled = false;
    (async () => {
      try {
        const { SocialLogin } = await import("@capgo/capacitor-social-login");
        if (cancelled) return;
        await SocialLogin.initialize({
          google: { webClientId: googleClientId },
        });
      } catch {
        // Button still works; login() will surface the error
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [nativeMode, googleClientId]);

  async function onGoogleClick() {
    if (busy) return;
    setError("");

    if (nativeMode) {
      setBusy(true);
      try {
        const { SocialLogin } = await import("@capgo/capacitor-social-login");
        await SocialLogin.initialize({
          google: { webClientId: googleClientId },
        });
        const res = await SocialLogin.login({
          provider: "google",
          options: {
            scopes: ["email", "profile"],
          },
        });
        const idToken =
          (res as { result?: { idToken?: string }; idToken?: string }).result?.idToken ||
          (res as { idToken?: string }).idToken;
        if (!idToken) {
          throw new Error("Google did not return an ID token. Check Android OAuth client SHA-1 setup.");
        }
        await handleCredential(idToken);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Google sign-in failed";
        if (/cancel|dismiss|closed/i.test(msg)) {
          setError("");
        } else {
          setError(msg);
        }
        setBusy(false);
      }
      return;
    }

    if (window.google?.accounts?.id) {
      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed()) {
          setError(
            `Google Sign-In unavailable (${notification.getNotDisplayedReason() || "blocked"}). Use email/password, or try again.`
          );
        }
      });
      return;
    }

    setError("Google Sign-In is still loading. Wait a moment and try again, or use email/password.");
  }

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
            type="submit"
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

          <div ref={wrapRef} className="relative w-full">
            <button
              type="button"
              disabled={busy}
              onClick={() => void onGoogleClick()}
              className="flex w-full items-center justify-center gap-3 rounded-full border border-cloud-200 bg-white px-4 py-2.5 text-sm font-medium text-navy-900 shadow-sm transition hover:bg-cloud-50 disabled:opacity-60"
            >
              <GoogleGlyph />
              Sign in with Google
            </button>
            {!nativeMode && (
              <div
                ref={googleBtnRef}
                className={`absolute inset-0 flex items-center justify-center overflow-hidden ${
                  googleReady ? "opacity-100" : "pointer-events-none opacity-0"
                }`}
                aria-hidden={!googleReady}
              />
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
