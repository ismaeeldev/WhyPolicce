import type { Metadata } from "next";

import { PricingCards } from "@/components/pricing/PricingCards";
import { ActiveInquiriesGate } from "@/components/pricing/ActiveInquiriesGate";

export const metadata: Metadata = {
  title: "Pricing — WhyPolice",
  description:
    "Posting is free. Upgrade a single inquiry for $2.99 to unlock more length and evidence, or subscribe as a verified attorney for $149/month to reach real cases.",
  openGraph: {
    title: "Pricing — WhyPolice",
    description:
      "Posting is free. Upgrade a single inquiry for $2.99 to unlock more length and evidence, or subscribe as a verified attorney for $149/month to reach real cases.",
    type: "website",
  },
};

export default function PricingPage() {
  return (
    <div className="relative overflow-hidden px-5 py-12 sm:px-6 sm:py-20">
      {/* UI polish pass: header was plain text on flat background with no
          visual anchor — same ambient-glow language as the hero/product
          principle sections gives the page a consistent point of visual
          interest instead of reading as a bare caption above the cards. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[420px] -translate-x-1/2 -translate-y-1/3 rounded-full opacity-[0.12] blur-3xl"
        style={{
          background: "radial-gradient(circle, var(--wp-accent-bright) 0%, transparent 70%)",
        }}
      />
      <div className="wp-page-intro relative mx-auto max-w-[680px] text-center mb-12">
        <div>
          <h1 className="font-display text-h1 sm:text-display-lg leading-[1.1] mb-4">
            Transparent, Equitable Access.
          </h1>
          <p className="text-body-lg text-text-secondary">
            No hidden fees. Post for free, upgrade only when necessary. Citizens may post
            and track inquiries at no cost. Upgrade individual posts for expanded text and
            media capacity. Verified attorneys subscribe to connect with active public
            inquiries.
          </p>
        </div>
      </div>
      <div className="relative">
        <PricingCards />
      </div>
      <ActiveInquiriesGate />
    </div>
  );
}
