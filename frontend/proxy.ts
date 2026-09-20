import { NextResponse, type NextRequest } from "next/server";

import { auth0 } from "@/lib/auth0";

/**
 * Route protection — AgentGuide/02_ApplicationFlow.md §2 and
 * AgentGuide/04_FolderStructure.md (protected route group). Uses `proxy.ts`,
 * not `middleware.ts` — Next.js 16 deprecates middleware.ts for the Node
 * runtime, and the installed Auth0 SDK's own docs recommend proxy.ts as the
 * current convention. See lib/auth0.ts for the fuller architecture note.
 */
// Forum rebuild, Milestone 2: /search, /history, /upgrade are the old RAG
// product's own protected routes, kept only because their pages/routes
// still exist and aren't being deleted this milestone. /inquiries/new
// (submit) is the new product's protected write action; the feed
// (/inquiries) and a single inquiry's thread stay public/read-only per
// the scope PDF, so they're deliberately NOT in this list. /account stays
// protected since both products still gate it. /attorneys/dashboard is
// the attorney portal (M2.4) — protected because it requires knowing
// which authenticated user's role/verification_status to check; the
// public /attorneys landing page itself is intentionally NOT prefixed
// here, since a logged-out visitor must be able to read about attorney
// signup before being forced to authenticate.
const PROTECTED_PREFIXES = [
  "/search",
  "/history",
  "/account",
  "/upgrade",
  "/inquiries/new",
  "/attorneys/dashboard",
];

export async function proxy(request: NextRequest) {
  const authResponse = await auth0.middleware(request);

  // Let the SDK's own /auth/* routes (login, logout, callback, profile) through untouched.
  if (request.nextUrl.pathname.startsWith("/auth")) {
    return authResponse;
  }

  const isProtected = PROTECTED_PREFIXES.some((prefix) =>
    request.nextUrl.pathname.startsWith(prefix),
  );

  if (isProtected) {
    const session = await auth0.getSession(request);
    if (!session) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("returnTo", request.nextUrl.pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return authResponse;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"],
};
