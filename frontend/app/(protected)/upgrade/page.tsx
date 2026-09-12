"use client";

import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";

import { PricingCards } from "@/components/pricing/PricingCards";
import { isBillingNotConfigured, useCreateCheckoutSession } from "@/hooks/useBilling";
import { useUser } from "@/hooks/useUser";
import { getUpgradeReasonCopy } from "@/lib/upgradeReasons";
import { useToastStore } from "@/stores/useToastStore";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Authenticated, contextual upgrade page — AgentGuide/02_ApplicationFlow.md
 * §3.5. Reuses PricingCards from Step 2 with a `reason` query param
 * explaining why the user landed here (mirrors the inline UpgradeModal's
 * copy, Step 5) and a real checkout-triggering CTA (Step 7) that's honest
 * about billing not being fully wired yet rather than a dead click.
 */
export default function UpgradePage() {
  const searchParams = useSearchParams();
  const reason = searchParams.get("reason");
  const copy = getUpgradeReasonCopy(reason);

  const { data: me } = useUser();
  const checkout = useCreateCheckoutSession();
  const showToast = useToastStore((s) => s.show);

  const handleUpgradeClick = () => {
    checkout.mutate(undefined, {
      onSuccess: (data) => {
        window.location.href = data.checkoutUrl;
      },
      onError: (error) => {
        showToast(
          isBillingNotConfigured(error)
            ? "Billing isn't set up yet — check back soon."
            : "Couldn't start checkout — try again shortly.",
        );
      },
    });
  };

  return (
    <div className="mx-auto w-full min-w-0 max-w-[880px] px-5 sm:px-6 py-16 sm:py-20 text-center">
      <motion.h1
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: EASE }}
        className="font-display text-3xl sm:text-4xl text-text-primary"
      >
        {copy.title}
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05, ease: EASE }}
        className="mt-3 text-body text-text-secondary max-w-lg mx-auto"
      >
        {copy.body}
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.1, ease: EASE }}
        className="mt-12"
      >
        <PricingCards
          currentTier={me?.tier ?? "free"}
          onUpgradeClick={handleUpgradeClick}
          upgradePending={checkout.isPending}
        />
      </motion.div>
    </div>
  );
}
