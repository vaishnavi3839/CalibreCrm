"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, clearTokens, setTokens } from "@/lib/api";

export type UserRole =
  | "super_admin"
  | "admin"
  | "rm"
  | "telecaller"
  | "instructor"
  | "accountant"
  | "student"
  | "parent";

export type User = {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  photo_url?: string;
  role: { id: string; name: UserRole; display_name: string };
  extra_permissions?: Record<string, unknown>;
};

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  loginWithGoogle: (idToken: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    try {
      const res = await api<User>("/api/v1/auth/me");
      setUser(res.data);
      localStorage.setItem("caa_user", JSON.stringify(res.data));
    } catch {
      setUser(null);
      clearTokens();
    }
  }, []);

  useEffect(() => {
    const cached = localStorage.getItem("caa_user");
    const access = localStorage.getItem("caa_access");
    if (cached && access) {
      try {
        setUser(JSON.parse(cached));
      } catch {
        /* ignore */
      }
      refreshMe().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [refreshMe]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api<{
      user: User;
      tokens: { access_token: string; refresh_token: string };
    }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, false);
    setTokens(res.data.tokens.access_token, res.data.tokens.refresh_token);
    localStorage.setItem("caa_user", JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const res = await api<{
      user: User;
      tokens: { access_token: string; refresh_token: string };
    }>("/api/v1/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }, false);
    setTokens(res.data.tokens.access_token, res.data.tokens.refresh_token);
    localStorage.setItem("caa_user", JSON.stringify(res.data.user));
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem("caa_refresh");
    try {
      if (refresh) {
        await api("/api/v1/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refresh }),
        }, false);
      }
    } catch {
      /* ignore */
    }
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, loginWithGoogle, logout, refreshMe }),
    [user, loading, login, loginWithGoogle, logout, refreshMe]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function dashboardPathForRole(role: UserRole): string {
  switch (role) {
    case "telecaller":
      return "/app/telecaller";
    case "student":
      return "/app/student";
    case "parent":
      return "/app/parent";
    case "instructor":
      return "/app/instructor";
    case "accountant":
      return "/app/finance";
    case "rm":
      return "/app/rm";
    default:
      return "/app/admin";
  }
}
