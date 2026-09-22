import type { Metadata } from "next";

import { ScrollReveal } from "@/components/marketing/ScrollReveal";

export const metadata: Metadata = {
  title: "Privacy — WhyPolice",
  description: "How WhyPolice handles your account, your posts, and your data.",
  openGraph: {
    title: "Privacy — WhyPolice",
    description: "How WhyPolice handles your account, your posts, and your data.",
    type: "website",
  },
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto w-full min-w-0 max-w-[680px] px-5 sm:px-6 py-12 sm:py-20">
      {/* UI polish pass: was missing ScrollReveal (its About/Terms siblings
          both have it), and the "coming soon" caveat had zero visual
          distinction from the substantive policy paragraphs above it
          besides muted color — now a real bordered callout so it reads
          as an intentional notice, not an afterthought trailing off. */}
      <div className="wp-page-intro">
        <p className="wp-eyebrow mb-4">Your trust matters</p>
        <h1 className="font-display text-h1 sm:text-display-lg leading-[1.1] mb-8">Privacy</h1>
      </div>
      <ScrollReveal className="flex flex-col gap-6 text-body text-text-secondary leading-relaxed">
        <p>
          Reading WhyPolice needs no account. We require an account to post,
          follow, or comment for one reason: to keep the forum free of bots
          and spam. It is not used to build an advertising profile.
        </p>
        <p>
          Your inquiries and comments are public by design — that&apos;s the
          point of a community forum. What we never make public is your
          contact information: an attorney reviewing your case sees your
          post, never your email, and can only reach you through the
          platform&apos;s own consultation-request flow, which you control.
        </p>
        <p>
          We do not sell your data, share it with advertisers, or use it to
          train models without your explicit consent.
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
