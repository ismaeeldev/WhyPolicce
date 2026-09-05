import type { Metadata } from "next";

import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { PricingCards } from "@/components/pricing/PricingCards";

export const metadata: Metadata = {
  title: "Pricing — WhyPolice",
  description:
    "Free for everyday search. Upgrade to Pro for deep search, advanced export, and priority streaming — $12/month.",
  openGraph: {
    title: "Pricing — WhyPolice",
    description:
      "Free for everyday search. Upgrade to Pro for deep search, advanced export, and priority streaming — $12/month.",
    type: "website",
  },
};

export default function PricingPage() {
  return (
    <div className="relative overflow-hidden px-6 py-20 sm:py-28">
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
      <ScrollReveal className="relative mx-auto max-w-[680px] text-center mb-14">
        <div>
          <h1 className="font-display text-display-lg leading-[1.1] mb-4">
            Simple pricing, no surprises.
          </h1>
          <p className="text-body-lg text-text-secondary">
            Start free. Upgrade only when you&apos;re actually searching harder
            than most people do.
          </p>
        </div>
      </ScrollReveal>
      <div className="relative">
        <PricingCards />
      </div>
    </div>
  );
}
