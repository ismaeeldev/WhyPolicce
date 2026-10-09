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
// still exist and aren't being deleted this milestone. The feed
// (/inquiries) and a single inquiry's thread stay public/read-only per
// the scope PDF, so they're deliberately NOT in this list. /account stays
// protected since both products still gate it. /attorneys/dashboard is
// the attorney portal (M2.4) — protected because it requires knowing
// which authenticated user's role/verification_status to check; the
// public /attorneys landing page itself is intentionally NOT prefixed
// here, since a logged-out visitor must be able to read about attorney
// signup before being forced to authenticate. /admin (new) is the
// admin panel — this only enforces "must be logged in at all" the same
// as every other protected prefix; the REAL admin-membership check
// (ADMIN_AUTH0_SUBS) happens server-side via GET /api/v1/admin/me,
// since proxy.ts has no DB access and can't know who's an admin. A
// logged-in non-admin reaching /admin gets a real "not authorized"
// page from the admin layout itself, not a silent redirect here.
//
// Scope Revision 1 §3.1 (AgentGuide/newscoperev1.md): /inquiries/new is
// intentionally NOT in this list anymore — the "deferred sign-up" flow
// lets a logged-out visitor fill out the form and only gates on the
// final Publish click (see app/inquiries/new/page.tsx's own auth check).
// The backend's create_inquiry endpoint independently requires a valid
// auth token (Depends(get_current_user)) regardless of this frontend
// gate, so removing this prefix does not expose a new unauthenticated
// write path — confirmed in backend/app/routers/inquiries.py before
// this change.
const PROTECTED_PREFIXES = [
  "/search",
  "/history",
  "/account",
  "/upgrade",
  "/attorneys/dashboard",
  "/admin",
];

export async function proxy(request: NextRequest) {
  // Internal QA fixtures (app/dev/*) must not exist in production: answer with
  // a real 404 rather than the empty shell the route layout would render.
  if (process.env.NODE_ENV === "production" && request.nextUrl.pathname.startsWith("/dev")) {
    return new NextResponse("Not found", { status: 404 });
  }

  const authResponse = await auth0.middleware(request);

  // Let the SDK's own /auth/* routes (login, logout, callback, profile) through untouched.
  if (request.nextUrl.pathname.startsWith("/auth")) {
    return authResponse;
  }

  // Match on a path-segment boundary so "/searchfoo" is not treated as "/search".
  const isProtected = PROTECTED_PREFIXES.some(
    (prefix) => request.nextUrl.pathname === prefix || request.nextUrl.pathname.startsWith(`${prefix}/`),
  );

  if (isProtected) {
    const session = await auth0.getSession(request);
    if (!session) {
      const loginUrl = new URL("/login", request.url);
      // Keep the query string so deep links survive the login round-trip.
      loginUrl.searchParams.set("returnTo", request.nextUrl.pathname + request.nextUrl.search);
      return NextResponse.redirect(loginUrl);
    }
  }

  return authResponse;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)"],
};
