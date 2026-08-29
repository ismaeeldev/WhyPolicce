import { Auth0Client } from "@auth0/nextjs-auth0/server";

/**
 * Auth0 SDK v4 client — AgentGuide/03_MasterPromptGuide.md Step 3.
 *
 * ARCHITECTURE NOTE: the folder structure guide (AgentGuide/04_FolderStructure.md)
 * describes a v3-era `app/api/auth/[...auth0]/route.ts` catch-all route handler.
 * The actually-installed SDK is v4, which uses a different pattern: no route
 * handler file at all — `auth0.middleware(req)` in middleware.ts mounts
 * /auth/login, /auth/logout, /auth/callback, /auth/profile automatically.
 * This is the correct, current SDK API, not a deviation to "fix" — logged as
 * an architecture adaptation in AgentGuide/05_PROJECT_STATE.md §2, same
 * pattern as the Tailwind v4 adaptation in Step 1.
 *
 * Reads AUTH0_DOMAIN / AUTH0_CLIENT_ID / AUTH0_CLIENT_SECRET / AUTH0_SECRET /
 * APP_BASE_URL from env automatically. AUTH0_AUDIENCE is NOT auto-read by the
 * SDK (confirmed via its source — only `authorizationParameters.audience`
 * passed here is honored) — without it, Auth0 issues an encrypted/opaque
 * access token instead of a verifiable RS256 JWT, which the backend's
 * JWKS-based verification in app/core/security.py can never validate. Found
 * via live testing: a real signup produced a token with `alg: dir, enc:
 * A256GCM` (JWE) and no audience claim, causing every /api/me call to 401
 * with "Signing key not found for this token".
 */
export const auth0 = new Auth0Client({
  authorizationParameters: {
    audience: process.env.AUTH0_AUDIENCE,
  },
});
