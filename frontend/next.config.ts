import type { NextConfig } from "next";

const API_ORIGIN = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Capacitor plugins ship uncompiled ESM that Next needs to transpile.
  transpilePackages: ["@capgo/capacitor-social-login", "@capacitor/core"],
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "api.dicebear.com" },
    ],
  },
  // Many pages use flexible API payloads; don't block production builds on style lint.
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Ensure the public Google client ID is always available to the browser bundle.
  env: {
    NEXT_PUBLIC_GOOGLE_CLIENT_ID:
      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ||
      "113963656390-odafike631l3st0onl83t4181b0vj75m.apps.googleusercontent.com",
  },
  async headers() {
    return [
      {
        source: "/login",
        headers: [
          { key: "Cache-Control", value: "no-store, no-cache, must-revalidate, max-age=0" },
        ],
      },
      {
        source: "/",
        headers: [
          { key: "Cache-Control", value: "no-store, max-age=0" },
        ],
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_ORIGIN}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${API_ORIGIN}/health`,
      },
      {
        source: "/uploads/:path*",
        destination: `${API_ORIGIN}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
