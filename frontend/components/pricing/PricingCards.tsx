"use client";

import { useUser } from "@auth0/nextjs-auth0";
import { Check, Minus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { BecomeAttorneyDialog } from "@/components/account/BecomeAttorneyDialog";

/**
 * Pricing — two genuinely separate billing shapes, not a tiered account plan:
 * a one-time $2.99 upgrade for a single citizen post, and a recurring
 * $149/month verified-attorney subscription. Shown side by side (like
 * plans that actually apply to the visitor.
 */

type Plan = {
  id: string;
  audience: string;
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  badge?: string;
  cta: string;
  href?: string;
  action?: "become-attorney";
  featured?: boolean;
  includes: string[];
};

const PLANS: Plan[] = [
    {
      id: "free",
      audience: "For citizens",
      name: "Free",
      price: "$0",
      cadence: "no time limit",
      blurb: "Share what happened and ask your community for help.",
      cta: "Post an inquiry",
      href: "/inquiries/new",
      includes: [
        "Posts up to 250 characters",
        "1 photo or document, up to 5 MB",
        "Edit or delete your inquiry any time",
        "Follow inquiries and get updates",
        "Post anonymously if you prefer",
      ],
    },
    {
      id: "upgrade",
      audience: "For citizens",
      name: "Full post",
      price: "$2.99",
      cadence: "one-time, per inquiry",
      blurb: "More room to explain and more evidence, for that one post.",
      cta: "Start an inquiry",
      href: "/inquiries/new",
      badge: "Most popular",
      featured: true,
      includes: [
        "Everything in Free, plus:",
        "No 250-character limit",
        "Up to 5 files, 50 MB in total",
        "Pay only for the posts that need it",
        "Upgrade from the post itself, any time",
      ],
    },
    {
      id: "attorney",
      audience: "For attorneys",
      name: "Verified attorney",
      price: "$149",
      cadence: "per month",
      blurb: "Full access to the case feed and direct outreach to citizens who need help.",
      cta: "Apply as an attorney",
      action: "become-attorney",
      badge: "Verification required",
      
      includes: [
        "Full access to the comprehensive case ledger",
        "Send formal consultation requests on active inquiries",
        "Track all your client requests in one place",
        "Verified badge on the platform",
        "Subject to bar number and jurisdiction review",
      ],
    },
];

type Row = { feature: string; free: string | boolean; full: string | boolean };
const COMPARISON: { group: string; rows: Row[] }[] = [
  {
    group: "Posting",
    rows: [
      { feature: "Post length", free: "250 characters", full: "Unlimited" },
      { feature: "Files per post", free: "1", full: "Up to 5" },
      { feature: "File size", free: "5 MB", full: "50 MB total" },
    ],
  },
  {
    group: "Your account",
    rows: [
      { feature: "Anonymous posting", free: true, full: true },
      { feature: "Edit or delete any time", free: true, full: true },
      { feature: "Follow inquiries", free: true, full: true },
    ],
  },
];

function Cell({ value }: { value: string | boolean }) {
  if (value === true) return <Check className="mx-auto h-4 w-4 text-accent" aria-label="Included" />;
  if (value === false) return <Minus className="mx-auto h-4 w-4 text-text-muted" aria-label="Not included" />;
  return <span className="text-text-primary">{value}</span>;
}

export function PricingCards() {
  const { user, isLoading } = useUser();
  const [attorneyDialogOpen, setAttorneyDialogOpen] = useState(false);
  const router = useRouter();
  const plans = PLANS;

  const ctaClass = (featured?: boolean) =>
    `mt-6 block w-full rounded-lg px-4 py-3 text-center text-body-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
      featured
        ? "bg-accent text-accent-foreground hover:bg-accent-hover"
        : "border border-border-strong text-text-primary hover:bg-bg-subtle"
    }`;

  return (
    <div className="mx-auto w-full max-w-[1120px]">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`flex flex-col rounded-2xl bg-bg-elevated p-7 sm:p-8 ${
              plan.featured ? "border-2 border-accent/60 shadow-card-lg" : "border-2 border-border-default shadow-card"
            }`}
          >
            <div className="flex h-6 items-center justify-between gap-2">
              <p className="text-caption font-semibold uppercase tracking-wider text-accent">{plan.audience}</p>
              {plan.badge && (
                <span className="rounded-full border border-accent/40 bg-accent/10 px-2.5 py-0.5 text-[11px] font-medium text-accent">
                  {plan.badge}
                </span>
              )}
            </div>
            <h2 className="mt-1.5 font-display text-h2 text-text-primary">{plan.name}</h2>
            <p className="mt-1.5 min-h-[2.75rem] text-body-sm text-text-secondary leading-relaxed">{plan.blurb}</p>

            <div className="mt-5 flex items-baseline gap-2">
              <span className="font-display text-display-lg text-text-primary tracking-tight tabular-nums">
                {plan.price}
              </span>
              <span className="text-body-sm text-text-muted">{plan.cadence}</span>
            </div>

            {plan.action === "become-attorney" ? (
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
                className={ctaClass(plan.featured)}
              >
                {plan.cta}
              </button>
            ) : (
              <Link href={plan.href ?? "/inquiries/new"} className={ctaClass(plan.featured)}>
                {plan.cta}
              </Link>
            )}

            <ul className="mt-7 flex flex-col gap-3 border-t border-border-default pt-6">
              {plan.includes.map((label) => (
                <li key={label} className="flex items-start gap-2.5 text-body-sm">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
                  <span className="text-text-primary leading-normal">{label}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <p className="mx-auto mt-6 max-w-[760px] text-center text-caption text-text-muted">
        Prices are in US dollars. The $2.99 fee is charged once per inquiry; the attorney subscription is billed
        monthly after your application is approved.
      </p>

      <div className="mx-auto mt-16 max-w-[1000px]">
        <h2 className="font-display text-h2 text-text-primary text-center">Compare citizen plans</h2>
        <div className="mt-6 overflow-hidden rounded-xl border border-border-default bg-bg-elevated">
          <table className="w-full table-fixed border-collapse text-left text-caption sm:text-body-sm">
            <thead>
              <tr className="border-b border-border-default bg-bg-subtle">
                <th scope="col" className="w-[34%] px-3 py-3 font-medium text-text-secondary sm:px-5">
                  <span className="sr-only">Feature</span>
                </th>
                {[
                  { name: "Free", cta: "Post", featured: false },
                  { name: "Full post", cta: "Start", featured: true },
                ].map((c) => (
                  <th key={c.name} scope="col" className="px-2 py-3 text-center font-medium text-text-primary sm:px-5">
                    <span className="block">{c.name}</span>
                    <Link
                      href="/inquiries/new"
                      className={`mt-2 inline-block rounded-md px-3 py-1 text-caption font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-accent outline-none ${
                        c.featured
                          ? "bg-accent text-accent-foreground hover:bg-accent-hover"
                          : "border border-border-strong text-text-primary hover:bg-bg-subtle"
                      }`}
                    >
                      {c.cta}
                    </Link>
                  </th>
                ))}
              </tr>
            </thead>
            {COMPARISON.map((section) => (
              <tbody key={section.group}>
                <tr className="bg-bg-subtle/60">
                  <th
                    colSpan={3}
                    scope="colgroup"
                    className="px-3 py-2 text-left font-mono text-[11px] font-medium uppercase tracking-wider text-text-muted sm:px-5"
                  >
                    {section.group}
                  </th>
                </tr>
                {section.rows.map((row) => (
                  <tr key={row.feature} className="border-t border-border-default">
                    <th scope="row" className="px-3 py-3 font-normal text-text-primary sm:px-5">
                      {row.feature}
                    </th>
                    <td className="px-2 py-3 text-center sm:px-5">
                      <Cell value={row.free} />
                    </td>
                    <td className="px-2 py-3 text-center sm:px-5">
                      <Cell value={row.full} />
                    </td>
                  </tr>
                ))}
              </tbody>
            ))}
          </table>
        </div>
      </div>

      <BecomeAttorneyDialog open={attorneyDialogOpen} onOpenChange={setAttorneyDialogOpen} />
    </div>
  );
}
