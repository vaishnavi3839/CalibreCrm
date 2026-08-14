// Prefer same-origin requests (Next.js rewrites proxy to FastAPI).
// Override with NEXT_PUBLIC_API_URL only when calling the API directly.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export type ApiEnvelope<T> = {
  statusCode: number;
  message: string;
  data: T;
};

function getTokens() {
  if (typeof window === "undefined") return { access: null as string | null, refresh: null as string | null };
  return {
    access: localStorage.getItem("caa_access"),
    refresh: localStorage.getItem("caa_refresh"),
  };
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem("caa_access", access);
  localStorage.setItem("caa_refresh", refresh);
}

export function clearTokens() {
  localStorage.removeItem("caa_access");
  localStorage.removeItem("caa_refresh");
  localStorage.removeItem("caa_user");
}

async function refreshAccess(): Promise<string | null> {
  const { refresh } = getTokens();
  if (!refresh) return null;
  const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const json = (await res.json()) as ApiEnvelope<{ tokens: { access_token: string; refresh_token: string }; user: unknown }>;
  setTokens(json.data.tokens.access_token, json.data.tokens.refresh_token);
  localStorage.setItem("caa_user", JSON.stringify(json.data.user));
  return json.data.tokens.access_token;
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  auth = true
): Promise<ApiEnvelope<T>> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    let { access } = getTokens();
    if (!access) access = await refreshAccess();
    if (access) headers.set("Authorization", `Bearer ${access}`);
  }

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401 && auth) {
    const newAccess = await refreshAccess();
    if (newAccess) {
      headers.set("Authorization", `Bearer ${newAccess}`);
      res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    }
  }

  const json = await res.json();
  if (!res.ok) {
    throw new Error(json?.message || "Request failed");
  }
  return json as ApiEnvelope<T>;
}

export { API_BASE };
