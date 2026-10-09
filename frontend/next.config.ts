import type { NextConfig } from "next";

// Baseline security headers for every route. A Content-Security-Policy is
// deliberately not set here: Auth0, Stripe and signed cloud-storage uploads
// need a per-environment allow-list that should be tuned against the real
// deployment rather than guessed.
const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },

  // Standalone output — AgentGuide/00_SCOPE.md §3 point 11 / Step 9. Produces
  // a minimal self-contained server (.next/standalone/server.js) with only
  // the deps actually used, which is what frontend/Dockerfile's runner stage
  // copies and runs — required for a reasonably small production image.
  output: "standalone",

  // Next.js 15+ blocks dev-server asset/HMR requests whose Origin header
  // doesn't match an allowed dev origin — by default that's "localhost"
  // ONLY, so opening the dev server via 127.0.0.1 silently 403s every JS
  // chunk and the app never hydrates (found via headless-browser testing;
  // curl alone doesn't surface this since it sends no Origin header).
  // If testing on a real phone over the LAN (per the responsiveness
  // requirement in AgentGuide/01_ThemeGuideline.md §3.1), add your
  // machine's printed "Network" IP here too — it's LAN/machine-specific,
  // so it's intentionally not hardcoded in checked-in config.
  allowedDevOrigins: ["localhost", "127.0.0.1"],
};

export default nextConfig;
