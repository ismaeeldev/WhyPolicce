import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AuthPageShell } from "@/components/auth/AuthPageShell";

export const metadata: Metadata = {
  title: "Log in — WhyPolice",
  description: "Log in to WhyPolice to post, follow, and reply on the forum.",
  openGraph: {
    title: "Log in — WhyPolice",
    description: "Log in to WhyPolice to post, follow, and reply on the forum.",
    type: "website",
  },
};

/**
 * Themed login page — AgentGuide/02_ApplicationFlow.md §3.2 and
 * AgentGuide/03_MasterPromptGuide.md Step 3. This is a real, on-brand page
 * (not a blind instant redirect) whose single CTA hands off to Auth0's
 * Universal Login, re-branded via the Auth0 dashboard per Step 3's manual
 * task. `AuthPageShell` (added during a UI modernization pass) gives this
 * previously-bare page the same entrance motion and ambient presence the
 * rest of the app has, instead of a static, empty-feeling card.
 */
function LoginContent({ returnTo }: { returnTo?: string }) {
  const loginHref = returnTo
    ? `/auth/login?returnTo=${encodeURIComponent(returnTo)}`
    : "/auth/login";

  return (
    <AuthPageShell>
      <h1 className="font-display text-h1 sm:text-display-lg leading-[1.1] mb-3">Welcome back.</h1>
      <p className="text-body text-text-secondary mb-8">
        Log in to pick up right where you left off.
      </p>
      <a
        href={loginHref}
        className="block rounded-sm bg-accent px-4 py-3 text-body font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        Continue to log in
      </a>
      <p className="mt-6 text-body-sm text-text-muted">
        New here?{" "}
        <Link href="/signup" className="text-accent underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
          Create an account
        </Link>
      </p>
    </AuthPageShell>
  );
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ returnTo?: string }>;
}) {
  const params = await searchParams;
  return (
    <Suspense>
      <LoginContent returnTo={params.returnTo} />
    </Suspense>
  );
}
