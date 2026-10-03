import type { NextConfig } from "next";

// The local live worker (pipeline.live) streams MJPEG + SSE from another port; allow it in development only.
const live = process.env.NODE_ENV === "development" ? " " + (process.env.NEXT_PUBLIC_CLOSECALL_LIVE_URL || "http://localhost:3503") : "";

const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'" + (process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""),
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:" + live,
  "media-src 'self'",
  "connect-src 'self'" + live,
  "font-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Server components and API routes read the pre-cached run from public/data with fs; bundle it.
  outputFileTracingIncludes: { "/**": ["./public/data/**"] },
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Content-Security-Policy", value: csp },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ],
    }];
  },
};

export default nextConfig;
