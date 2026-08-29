"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AuthPageShell } from "@/components/auth/AuthPageShell";

const PENDING_QUERY_KEY = "wp_pending_query";

/**
 * Client half of the signup page — split out from app/signup/page.tsx so
 * that file can stay a Server Component and export `metadata` (Next.js
 * requires metadata exports from Server Components only). Found via the
 * Step 1-8 audit: the whole page was previously "use client" just to read
 * sessionStorage here, which silently meant /signup had no page title/
 * description/OpenGraph at all — every sibling public page had one.
 */
export function SignupContent() {
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);

  useEffect(() => {
    // Reading sessionStorage is exactly the "external system" case an effect
    // is for — same pattern as the theme-preview contrast readout in Step 1.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPendingQuery(sessionStorage.getItem(PENDING_QUERY_KEY));
  }, []);

  return (
    <AuthPageShell maxWidthClassName="max-w-[440px]">
      <h1 className="font-display text-display-lg leading-[1.1] mb-3">
        Create your account.
      </h1>
      <p className="text-body text-text-secondary mb-6">
        One quick step keeps the platform free of bots and spam — that&apos;s
        the only reason it&apos;s here.
      </p>

      {pendingQuery && (
        <div className="mb-6 rounded-md border border-border-default bg-bg-elevated p-4 text-left">
          <p className="text-caption text-text-muted uppercase tracking-wide mb-1">
            We kept your question
          </p>
          <p className="text-body-sm text-text-primary">&ldquo;{pendingQuery}&rdquo;</p>
        </div>
      )}

      <a
        href="/auth/login?screen_hint=signup&returnTo=/search"
        className="block rounded-sm bg-accent px-4 py-3 text-body font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        Continue to sign up
      </a>
      <p className="mt-6 text-body-sm text-text-muted">
        Already have an account?{" "}
        <Link href="/login" className="text-accent underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
          Log in
        </Link>
      </p>
    </AuthPageShell>
  );
}
