import type { Metadata } from "next";

import { PricingFaq } from "@/components/pricing/PricingFaq";
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
    <div className="px-5 py-14 sm:px-6 sm:py-20">
      <div className="wp-page-intro mx-auto mb-12 max-w-[680px] text-center">
        <h1 className="font-display text-h1 sm:text-display-lg leading-[1.1] tracking-tight text-text-primary">
          Plans that work for everyone seeking accountability
        </h1>
        <p className="mx-auto mt-4 max-w-[560px] text-body-lg leading-relaxed text-text-secondary">
          Citizens post for free and upgrade a single post only when needed. Verified attorneys
          subscribe to reach active inquiries.
        </p>
      </div>
      <PricingCards />
      <ActiveInquiriesGate />
      <PricingFaq />
    </div>
  );
}
