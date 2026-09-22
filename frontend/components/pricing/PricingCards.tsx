"use client";

import { Check } from "lucide-react";
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
  audience: string;
  name: string;
  price: string;
  cadence: string;
  description: string;
  cta: string;
  href: string;
  featured?: boolean;
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
    features: [
      "Publish an inquiry up to 250 characters",
      "Edit or delete your own posts anytime",
      "Follow other inquiries and get replies",
      "Attach 1 photo or document up to 5MB",
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
      "Publish past the 250-character limit",
      "Attach up to 5 files, 50MB total",
      "Applies once, to the specific inquiry you upgrade",
      "No subscription — pay only when you need it",
    ],
  },
  {
    audience: "For attorneys",
    name: "Attorney subscription",
    price: "$149",
    cadence: "/month",
    description: "Full access to the case feed and the ability to reach out directly to citizens who need help.",
    cta: "Apply as an attorney",
    href: "/account",
    features: [
      "See every real case in the feed, not a preview",
      "Request a consultation directly on any inquiry",
      "Track your requests and their status in one place",
      "Requires a verified bar number and jurisdiction",
    ],
  },
];

export function PricingCards() {
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 max-w-[1100px] mx-auto">
      {PLANS.map((plan, i) => (
        <motion.div
          key={plan.name}
          custom={i}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-40px" }}
          variants={cardVariants}
          className={`wp-plan-card relative rounded-lg bg-bg-elevated p-6 sm:p-8 text-left transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-card-lg ${
            plan.featured
              ? "border border-accent shadow-card"
              : "border border-border-default"
          }`}
        >
          {!plan.featured && (
            <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-lg">
              <div
                aria-hidden="true"
                className="absolute -right-8 -top-8 h-32 w-32 rounded-full opacity-[0.06]"
                style={{ background: "radial-gradient(circle, var(--wp-text-primary) 0%, transparent 70%)" }}
              />
            </div>
          )}

          {plan.featured && (
            <span className="absolute -top-3 left-6 rounded-full bg-accent-subtle px-2.5 py-0.5 text-caption font-medium text-text-primary">
              Most useful
            </span>
          )}

          <p className="text-caption font-medium uppercase tracking-wide text-text-muted">
            {plan.audience}
          </p>
          <h2 className="mt-1.5 text-h2 font-semibold">{plan.name}</h2>
          <p className="mt-1 text-body-sm text-text-secondary">{plan.description}</p>

          <div className="mt-7 flex items-baseline gap-2">
            <span className="font-display text-display-lg text-text-primary">{plan.price}</span>
            <span className="text-body-sm text-text-muted">{plan.cadence}</span>
          </div>

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

          <ul className="mt-7 flex flex-col gap-4 border-t border-border-default pt-6">
            {plan.features.map((label) => (
              <li key={label} className="flex items-start gap-2.5 text-body-sm">
                <Check className="h-4 w-4 shrink-0 mt-0.5 text-accent-bright" />
                <span className="text-text-primary">{label}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      ))}
    </div>
  );
}
