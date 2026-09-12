import type { Metadata } from "next";
import Link from "next/link";

import { ScrollReveal } from "@/components/marketing/ScrollReveal";

export const metadata: Metadata = {
  title: "Terms — WhyPolice",
  description: "The terms of using WhyPolice.",
  openGraph: {
    title: "Terms — WhyPolice",
    description: "The terms of using WhyPolice.",
    type: "website",
  },
};

export default function TermsPage() {
  return (
    <div className="mx-auto w-full min-w-0 max-w-[680px] px-5 sm:px-6 py-12 sm:py-20">
      <div className="wp-page-intro">
        <p className="wp-eyebrow mb-4">The essentials</p>
        <h1 className="font-display text-h1 sm:text-display-lg leading-[1.1] mb-8">Terms</h1>
      </div>
      <ScrollReveal className="flex flex-col gap-6 text-body text-text-secondary leading-relaxed">
        <p>
          By creating a WhyPolice account, you agree to use the service for
          legitimate search purposes and not to abuse, scrape, or attempt to
          circumvent the platform&apos;s rate limits or subscription tiers.
        </p>
        <p>
          Free and Pro plans are described on our{" "}
          <Link href="/pricing" className="text-accent underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
            pricing page
          </Link>
          . We may adjust plan limits or pricing with reasonable notice.
        </p>
        {/* Same treatment as Privacy's matching caveat — a real bordered
            callout instead of muted text drifting off the paragraph list. */}
        <div className="rounded-md border border-dashed border-border-strong bg-bg-subtle p-4">
          <p className="text-text-muted text-body-sm">
            This page will be expanded with complete terms of service ahead
            of public launch.
          </p>
        </div>
      </ScrollReveal>
    </div>
  );
}
