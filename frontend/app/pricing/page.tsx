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
    <div className="px-6 py-20 sm:py-28">
      <ScrollReveal className="mx-auto max-w-[680px] text-center mb-14">
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
      <PricingCards />
    </div>
  );
}
