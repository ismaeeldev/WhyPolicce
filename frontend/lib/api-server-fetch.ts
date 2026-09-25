/**
 * Server-only counterpart to lib/api-client.ts's apiFetch — used
 * exclusively by Server Component prefetches (currently just
 * app/page.tsx's home-feed prefetch).
 *
 * Real bug found and fixed: apiFetch's `getAccessToken` import resolves
 * to `@auth0/nextjs-auth0`'s CLIENT helper (confirmed via the installed
 * package's own export map — the bare package specifier always points
 * at dist/client/index.js), which does `fetch("/auth/access-token")` — a
 * browser-relative URL with no origin to resolve against on the server.
 * Calling apiFetch from a Server Component (this file's whole reason to
 * exist) made that call take ~20-25s before falling through to its own
 * catch block, turning a fast server-prefetch optimization into a
 * regression far worse than the client-only fetch it was meant to
 * replace. The real server-safe equivalent is auth0.getAccessToken()
 * from the app's own already-configured Auth0Client instance
 * (lib/auth0.ts) — its own SDK source documents that calling it from a
 * Server Component won't persist a refreshed token, which is fine here:
 * this is a read-only, best-effort prefetch, never a mutation.
 */
import { auth0 } from "@/lib/auth0";
import { ApiError } from "@/lib/api-client";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export async function serverApiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token: string | undefined;
  try {
    token = (await auth0.getAccessToken())?.token;
  } catch {
    // No session — request proceeds unauthenticated, correct for a
    // public endpoint (the only kind this helper is used for today).
  }

  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(0, "network_error", "We couldn't reach the server — check your connection.");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: "unknown_error", message: res.statusText }));
    throw new ApiError(res.status, body.error ?? "unknown_error", body.message ?? res.statusText);
  }

  return res.json() as Promise<T>;
}
