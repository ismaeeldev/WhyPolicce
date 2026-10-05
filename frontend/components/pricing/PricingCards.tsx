"use client";

import { useUser } from "@auth0/nextjs-auth0";
import { Check } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useState } from "react";

import { BecomeAttorneyDialog } from "@/components/account/BecomeAttorneyDialog";

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
 * Citizen vs. attorney pricing — forum rebuild. Replaces the old
 * RAG-search product's Free/Pro subscription-tier comparison (retired
 * per the scope PDF's "What We Are No Longer Building On" section)
 * with the forum's own two, genuinely separate billing shapes: a
 * one-time $2.99 citizen inquiry upgrade (M2.3/M3.2) and a recurring
 * $149/month attorney subscription (M2.4/M3.2) — not a tiered
 * account-wide plan, since these apply to different things (a single
 * post vs. an attorney's whole account) for different audiences.
 */

type Plan = {
  id?: "become-attorney";
  audience: string;
  name: string;
  price: string;
  cadence: string;
  description: string;
  cta: string;
  href: string;
  featured?: boolean;
  // Real UX bug found during a UI audit: the "Upgrade a post" card's CTA
  // never starts the $2.99 upgrade directly (there's no inquiry_id to
  // upgrade until one exists) — it just links to the new-inquiry form,
  // same as "Post for free". Styling it as the solid-fill primary button
  // purely because the card is `featured` made the most misleading CTA
  // on the page look like the most actionable one. This flag decouples
  // "is the highlighted card" from "is this CTA a direct purchase action".
  ctaIsDirectAction?: boolean;
  features: string[];
};

const PLANS: Plan[] = [
  {
    audience: "For citizens",
    name: "Post an inquiry",
    price: "$0",
    cadence: "to start",
    description: "Share what happened and ask your community for help — free, no time limit.",
    cta: "Post for free",
    href: "/inquiries/new",
    ctaIsDirectAction: true,
    features: [
      "Publish inquiries up to 250 characters",
      "Edit or delete your inquiries at any time",
      "Follow active inquiries and receive updates",
      "Attach 1 photo or document (up to 5MB)",
    ],
  },
  {
    audience: "For citizens",
    name: "Upgrade a post",
    price: "$2.99",
    cadence: "one-time, per inquiry",
    description: "Need more room to explain, or more evidence attached? Unlock it for that one post.",
    cta: "Available from your inquiry",
    href: "/inquiries/new",
    featured: true,
    features: [
      "Remove the 250-character limit for comprehensive detail",
      "Attach up to 5 files (maximum 50MB total)",
      "One-time fee applied exclusively to the selected inquiry",
      "Non-recurring; pay only as needed",
    ],
  },
  {
    id: "become-attorney",
    audience: "For attorneys",
    name: "Attorney subscription",
    price: "$149",
    cadence: "/month",
    description: "Full access to the case feed and the ability to reach out directly to citizens who need help.",
    cta: "Apply as an attorney",
    href: "/account",
    ctaIsDirectAction: true,
    features: [
      "Full access to the comprehensive case ledger",
      "Submit formal consultation requests for active inquiries",
      "Centralized tracking for all active client requests",
      "Subject to active bar number and jurisdiction verification.",
    ],
  },
];

export function PricingCards() {
  const { user, isLoading } = useUser();
  const [attorneyDialogOpen, setAttorneyDialogOpen] = useState(false);
  const router = useRouter();

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 max-w-[1100px] mx-auto">
      {PLANS.map((plan, i) => (
        <motion.div
          key={plan.name}
          custom={i}
          initial="hidden"
          // Real bug found by a live UI audit: whileInView + a real
          // paying tier (Attorney subscription, $149/month, the third
          // card) staying invisible on some real scroll patterns is an
          // unacceptable risk on a pricing page, whatever the exact
          // automation-vs-real-browser cause turns out to be — a visitor
          // who can't see a plan can't buy it. animate="show" always
          // renders every card immediately on mount instead of
          // conditionally on scroll visibility; the same entrance
          // motion still plays via the initial->show variant transition,
          // just not gated behind an IntersectionObserver trigger that
          // has no real product upside here (this page is short enough
          // that "reveal on scroll" isn't hiding anything meaningfully
          // below an unreachable fold in the first place).
          animate="show"
          variants={cardVariants}
          className={`wp-surface-card wp-plan-card relative rounded-2xl bg-bg-elevated/90 backdrop-blur-sm p-6 sm:p-8 text-left transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-card-lg flex flex-col justify-between ${
            plan.featured
              ? "border-2 border-accent/60 shadow-card ring-1 ring-accent/20"
              : "border border-border-default/80 hover:border-border-strong"
          }`}
        >
          {!plan.featured && (
            <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl">
              <div
                aria-hidden="true"
                className="absolute -right-8 -top-8 h-32 w-32 rounded-full opacity-[0.06]"
                style={{ background: "radial-gradient(circle, var(--wp-text-primary) 0%, transparent 70%)" }}
              />
            </div>
          )}

          {plan.featured && (
            <div className="absolute -top-3.5 left-6 rounded-full bg-gradient-to-r from-accent to-accent-hover px-3 py-0.5 text-caption font-semibold text-accent-foreground shadow-sm">
              ★ Most popular
            </div>
          )}

          <div>
            <p className="text-caption font-semibold uppercase tracking-wider text-accent-bright">
              {plan.audience}
            </p>
            <h2 className="mt-1.5 text-h2 font-serif font-semibold text-text-primary">{plan.name}</h2>
            <p className="mt-1 text-body-sm text-text-secondary leading-relaxed">{plan.description}</p>

            <div className="mt-6 flex items-baseline gap-2">
              <span className="font-display text-display-lg text-text-primary tracking-tight">{plan.price}</span>
              <span className="text-body-sm text-text-muted">{plan.cadence}</span>
            </div>
          </div>

          <div>
            {plan.id === "become-attorney" ? (
              <button
                type="button"
                disabled={isLoading}
                onClick={() => {
                  if (!user) {
                    router.push(`/login?returnTo=${encodeURIComponent("/pricing")}`);
                    return;
                  }
                  setAttorneyDialogOpen(true);
                }}
                className="mt-6 block w-full rounded-xl bg-accent px-4 py-3 text-center text-body-sm font-semibold text-accent-foreground transition-all duration-200 hover:bg-accent-hover hover:shadow-md active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {plan.cta}
              </button>
            ) : (
              <Link
                href={plan.href}
                className={`mt-6 block rounded-xl px-4 py-3 text-center text-body-sm font-semibold transition-all duration-200 active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
                  plan.ctaIsDirectAction
                    ? "bg-accent text-accent-foreground hover:bg-accent-hover hover:shadow-md"
                    : "border border-border-strong text-text-primary hover:bg-bg-subtle hover:border-accent/40"
                }`}
              >
                {plan.cta}
              </Link>
            )}

            <ul className="mt-7 flex flex-col gap-3.5 border-t border-border-default/70 pt-6">
              {plan.features.map((label) => (
                <li key={label} className="flex items-start gap-2.5 text-body-sm">
                  <Check className="h-4 w-4 shrink-0 mt-0.5 text-accent-bright" />
                  <span className="text-text-primary leading-normal">{label}</span>
                </li>
              ))}
            </ul>
          </div>
        </motion.div>
      ))}
      <BecomeAttorneyDialog open={attorneyDialogOpen} onOpenChange={setAttorneyDialogOpen} />
    </div>
  );
}
