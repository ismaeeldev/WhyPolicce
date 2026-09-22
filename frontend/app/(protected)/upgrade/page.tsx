"use client";

import { Check } from "lucide-react";
import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";

import { isBillingNotConfigured, useCreateCheckoutSession } from "@/hooks/useBilling";
import { useUser } from "@/hooks/useUser";
import { getUpgradeReasonCopy } from "@/lib/upgradeReasons";
import { useToastStore } from "@/stores/useToastStore";

const EASE = [0.22, 1, 0.36, 1] as const;

const PRO_HIGHLIGHTS = [
  "Deep search — up to 50 intensive queries/day",
  "Advanced export — PDF, Markdown, bulk history",
  "Priority streaming during peak hours",
];

/**
 * Old RAG-search product's Pro-upgrade page — retained, not extended,
 * per the scope PDF's "What We Are No Longer Building On" section.
 * Only reachable from within the retired /search feature's own
 * gated-search paywall (components/shared/UpgradeModal.tsx), which
 * still exists and still works; no live link anywhere in the new
 * forum product points here. Kept as a small, self-contained card
 * (not sharing components/pricing/PricingCards, which was rebuilt for
 * the forum's own separate $2.99/$149-per-month billing shapes) so
 * this old feature keeps working exactly as before without being
 * entangled with the new pricing page's content.
 */
export default function UpgradePage() {
  const searchParams = useSearchParams();
  const reason = searchParams.get("reason");
  const copy = getUpgradeReasonCopy(reason);

  const { data: me } = useUser();
  const checkout = useCreateCheckoutSession();
  const showToast = useToastStore((s) => s.show);

  const isPro = me?.tier === "pro";

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
    <div className="mx-auto w-full min-w-0 max-w-[560px] px-5 sm:px-6 py-16 sm:py-20 text-center">
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
        className="mt-12 rounded-lg border border-accent bg-bg-elevated p-6 sm:p-8 text-left shadow-card"
      >
        <h2 className="text-h2 font-semibold">Pro</h2>
        <div className="mt-4 flex items-baseline gap-2">
          <span className="font-display text-display-lg text-text-primary">$12</span>
          <span className="text-body-sm text-text-muted">/month</span>
        </div>

        {isPro ? (
          <button
            type="button"
            disabled
            className="mt-6 block w-full rounded-sm border border-border-strong px-4 py-2.5 text-center text-body-sm font-medium text-text-muted cursor-default"
          >
            Current plan
          </button>
        ) : (
          <button
            type="button"
            onClick={handleUpgradeClick}
            disabled={checkout.isPending}
            className="mt-6 block w-full rounded-sm bg-accent px-4 py-2.5 text-center text-body-sm font-medium text-accent-foreground transition-all hover:bg-accent-hover active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-60 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {checkout.isPending ? "Starting checkout…" : "Upgrade to Pro"}
          </button>
        )}

        <ul className="mt-7 flex flex-col gap-4 border-t border-border-default pt-6">
          {PRO_HIGHLIGHTS.map((label) => (
            <li key={label} className="flex items-start gap-2.5 text-body-sm">
              <Check className="h-4 w-4 shrink-0 mt-0.5 text-accent-bright" />
              <span className="text-text-primary">{label}</span>
            </li>
          ))}
        </ul>
      </motion.div>
    </div>
  );
}
