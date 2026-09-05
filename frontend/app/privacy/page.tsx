import type { Metadata } from "next";

import { ScrollReveal } from "@/components/marketing/ScrollReveal";

export const metadata: Metadata = {
  title: "Privacy — WhyPolice",
  description: "How WhyPolice handles your account, your searches, and your data.",
  openGraph: {
    title: "Privacy — WhyPolice",
    description: "How WhyPolice handles your account, your searches, and your data.",
    type: "website",
  },
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-[680px] px-6 py-20 sm:py-28">
      {/* UI polish pass: was missing ScrollReveal (its About/Terms siblings
          both have it), and the "coming soon" caveat had zero visual
          distinction from the substantive policy paragraphs above it
          besides muted color — now a real bordered callout so it reads
          as an intentional notice, not an afterthought trailing off. */}
      <ScrollReveal>
        <h1 className="font-display text-display-lg leading-[1.1] mb-8">Privacy</h1>
      </ScrollReveal>
      <ScrollReveal className="space-y-6 text-body text-text-secondary leading-relaxed">
        <p>
          We require an account to search WhyPolice for one reason: to keep
          the platform free of bots and spam. It is not used to build an
          advertising profile.
        </p>
        <p>
          Your search history is stored so you can revisit it, and it is
          visible only to you. You can export any session or clear your
          entire history at any time from your account.
        </p>
        <p>
          We do not sell your searches, share them with advertisers, or use
          them to train models without your explicit consent.
        </p>
        <div className="rounded-md border border-dashed border-border-strong bg-bg-subtle p-4">
          <p className="text-text-muted text-body-sm">
            This page will be expanded with a complete privacy policy ahead
            of public launch.
          </p>
        </div>
      </ScrollReveal>
    </div>
  );
}
