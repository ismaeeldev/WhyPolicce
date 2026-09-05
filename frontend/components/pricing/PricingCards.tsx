"use client";

import { Check, Lock } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

const EASE = [0.22, 1, 0.36, 1] as const;

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: EASE, delay: i * 0.08 },
  }),
};

/**
 * Free vs Pro comparison — AgentGuide/01_ThemeGuideline.md §4.5.
 * Reused as-is on /pricing (Step 2, public, no props) and, contextually, on
 * /upgrade (Step 7, authenticated — `currentTier`/`onUpgradeClick` switch
 * the CTAs from "go to signup" to "you're already here"/"start checkout").
 */

type Plan = {
  name: string;
  price: string;
  cadence: string;
  description: string;
  cta: string;
  href: string;
  featured?: boolean;
  features: { label: string; included: boolean }[];
};

const PLANS: Plan[] = [
  {
    name: "Free",
    price: "$0",
    cadence: "forever",
    description: "Everything you need for everyday search.",
    cta: "Start for free",
    href: "/signup",
    features: [
      { label: "Unlimited standard search, streamed live", included: true },
      { label: "Full session history", included: true },
      { label: "Export any session as JSON, anytime", included: true },
      { label: "Personal memory notes", included: true },
      { label: "Deep search — up to 50 intensive queries/day", included: false },
      { label: "Advanced export — PDF, Markdown, bulk history", included: false },
    ],
  },
  {
    name: "Pro",
    price: "$12",
    cadence: "/month",
    description: "For research, deadlines, and heavier days.",
    cta: "Upgrade to Pro",
    href: "/signup",
    featured: true,
    features: [
      { label: "Everything in Free", included: true },
      { label: "Deep search — up to 50 intensive queries/day", included: true },
      { label: "Advanced export — PDF, Markdown, bulk history", included: true },
      { label: "Priority streaming during peak hours", included: true },
      { label: "Personal memory notes", included: true },
      { label: "Full session history", included: true },
    ],
  },
];

type AuthenticatedProps = {
  /** When set, CTAs switch from "go to signup" links to tier-aware actions:
   * a disabled "Current plan" state for the plan the user is already on,
   * and a real checkout-triggering button for the Pro upgrade path. */
  currentTier?: "free" | "pro";
  onUpgradeClick?: () => void;
  upgradePending?: boolean;
};

export function PricingCards({ currentTier, onUpgradeClick, upgradePending }: AuthenticatedProps = {}) {
  const authenticated = currentTier !== undefined;

  return (
    <div className="grid gap-6 sm:grid-cols-2 max-w-[880px] mx-auto">
      {PLANS.map((plan, i) => {
        const planTier = plan.name === "Pro" ? "pro" : "free";
        const isCurrentPlan = authenticated && currentTier === planTier;

        return (
        <motion.div
          key={plan.name}
          custom={i}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-40px" }}
          variants={cardVariants}
          className={`relative overflow-hidden rounded-lg bg-bg-elevated p-6 sm:p-8 transition-shadow duration-200 hover:shadow-card ${
            plan.featured
              ? "border-2 border-accent shadow-card"
              : "border border-border-default"
          }`}
        >
          {/* Free card previously read as a plain afterthought next to
              Pro's border/shadow/badge — UI polish pass gives it its own
              quiet visual identity (a soft corner texture) instead of
              just "the un-highlighted one." */}
          {!plan.featured && (
            <div
              aria-hidden="true"
              className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full opacity-[0.06]"
              style={{ background: "radial-gradient(circle, var(--wp-text-primary) 0%, transparent 70%)" }}
            />
          )}

          {plan.featured && (
            <span className="absolute -top-3 left-6 rounded-full bg-accent-subtle px-2.5 py-0.5 text-caption font-medium text-text-primary">
              Most popular
            </span>
          )}

          <h2 className="text-h2 font-semibold">{plan.name}</h2>
          <p className="mt-1 text-body-sm text-text-secondary">{plan.description}</p>

          <div className="mt-5 flex items-baseline gap-1">
            <span className="font-display text-4xl text-text-primary">{plan.price}</span>
            <span className="text-body-sm text-text-muted">{plan.cadence}</span>
          </div>

          {isCurrentPlan ? (
            <button
              type="button"
              disabled
              className="mt-6 block w-full rounded-sm border border-border-strong px-4 py-2.5 text-center text-body-sm font-medium text-text-muted cursor-default"
            >
              Current plan
            </button>
          ) : authenticated && plan.featured ? (
            <button
              type="button"
              onClick={onUpgradeClick}
              disabled={upgradePending}
              className="mt-6 block w-full rounded-sm bg-accent px-4 py-2.5 text-center text-body-sm font-medium text-accent-foreground transition-all hover:bg-accent-hover active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-60 disabled:cursor-not-allowed disabled:active:scale-100"
            >
              {upgradePending ? "Starting checkout…" : plan.cta}
            </button>
          ) : authenticated ? null : (
            <Link
              href={plan.href}
              className={`mt-6 block rounded-sm px-4 py-2.5 text-center text-body-sm font-medium transition-all active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
                plan.featured
                  ? "bg-accent text-accent-foreground hover:bg-accent-hover"
                  : "border border-border-strong text-text-primary hover:bg-bg-subtle"
              }`}
            >
              {plan.cta}
            </Link>
          )}

          <ul className="mt-7 space-y-3">
            {plan.features.map((f) => (
              <li key={f.label} className="flex items-start gap-2.5 text-body-sm">
                {f.included ? (
                  <Check className="h-4 w-4 shrink-0 mt-0.5 text-accent-bright" />
                ) : (
                  <Lock className="h-4 w-4 shrink-0 mt-0.5 text-text-muted" />
                )}
                <span className={f.included ? "text-text-primary" : "text-text-muted"}>
                  {f.label}
                </span>
              </li>
            ))}
          </ul>
        </motion.div>
        );
      })}
    </div>
  );
}
