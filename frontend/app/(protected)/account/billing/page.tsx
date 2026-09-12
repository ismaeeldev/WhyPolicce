"use client";

import { motion } from "framer-motion";
import { ArrowLeft, Receipt, Sparkles } from "lucide-react";
import Link from "next/link";

import { useUser } from "@/hooks/useUser";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Billing entry point — AgentGuide/02_ApplicationFlow.md §3.6, stub in MVP.
 * No Stripe customer-portal endpoint is in scope yet (only checkout-session
 * and webhook, per the route list) — honest disabled state with a tooltip
 * rather than a dead click, per Step 7's master prompt point 5. Brought up
 * to the same visual bar as the rest of the app during a UI modernization
 * pass — this page previously had zero motion and a flat, generic card.
 */
export default function BillingPage() {
  const { data: me } = useUser();
  const tier = me?.tier ?? "free";

  return (
    <div className="mx-auto w-full min-w-0 max-w-[560px] px-5 sm:px-6 py-16 sm:py-20">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, ease: EASE }}
      >
        <Link
          href="/account"
          className="mb-6 inline-flex items-center gap-1.5 text-body-sm text-text-secondary hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to account
        </Link>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05, ease: EASE }}
        className="font-display text-h1 text-text-primary"
      >
        Billing
      </motion.h1>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1, ease: EASE }}
                className="mt-6 rounded-md border border-border-default bg-bg-elevated p-5 sm:p-6 shadow-card transition-shadow duration-150 hover:shadow-card"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-body-sm text-text-secondary">Current plan</p>
            <span
              className={`mt-1.5 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-caption font-medium ${
                tier === "pro" ? "bg-accent-subtle text-text-primary" : "bg-bg-subtle text-text-secondary"
              }`}
            >
              {tier === "pro" && <Sparkles className="h-3 w-3 text-accent-bright" />}
              {tier === "pro" ? "Pro" : "Free"}
            </span>
          </div>
          {/* UI polish pass: a lone flat circle read as a bare
              placeholder icon — a soft ring + subtle glow gives the
              "coming soon" chip a bit more presence without implying
              billing is more built-out than it actually is. */}
          <div className="relative flex h-10 w-10 shrink-0 items-center justify-center">
            <div className="absolute inset-0 rounded-full bg-accent-subtle opacity-40 blur-md" />
            <div className="relative flex h-10 w-10 items-center justify-center rounded-full border border-border-default bg-bg-subtle">
              <Receipt className="h-4 w-4 text-text-muted" strokeWidth={1.5} />
            </div>
          </div>
        </div>

        <button
          type="button"
          disabled
          title="Billing portal coming soon"
          className="mt-5 block w-full rounded-sm border border-border-default px-4 py-2.5 text-center text-body-sm text-text-muted opacity-60 cursor-not-allowed"
        >
          Manage billing — coming soon
        </button>
        <p className="mt-2 text-caption text-text-muted text-center">
          Invoices and payment methods will be manageable here once billing is fully set up.
        </p>
      </motion.div>
    </div>
  );
}
