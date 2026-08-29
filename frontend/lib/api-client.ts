/**
 * Typed fetch wrapper to the FastAPI backend — AgentGuide/03_MasterPromptGuide.md
 * Step 4. Attaches the Auth0 access token as a Bearer header. The access
 * token itself is fetched via the SDK's client-side accessToken helper at
 * call time (not stored), so this stays safe to call from client components.
 */
import { getAccessToken } from "@auth0/nextjs-auth0";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token: string | undefined;
  try {
    token = await getAccessToken();
  } catch {
    // No session — request proceeds unauthenticated, backend will 401 it,
    // which is the correct behavior for a protected endpoint.
  }

  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: "unknown_error", message: res.statusText }));
    throw new ApiError(res.status, body.error ?? "unknown_error", body.message ?? res.statusText);
  }

  return res.json() as Promise<T>;
}
