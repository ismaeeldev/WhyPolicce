import { NextResponse, type NextRequest } from "next/server";

import { auth0 } from "@/lib/auth0";

/**
 * Route protection — AgentGuide/02_ApplicationFlow.md §2 and
 * AgentGuide/04_FolderStructure.md (protected route group). Uses `proxy.ts`,
 * not `middleware.ts` — Next.js 16 deprecates middleware.ts for the Node
 * runtime, and the installed Auth0 SDK's own docs recommend proxy.ts as the
 * current convention. See lib/auth0.ts for the fuller architecture note.
 */
const PROTECTED_PREFIXES = ["/search", "/history", "/account", "/upgrade"];

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
