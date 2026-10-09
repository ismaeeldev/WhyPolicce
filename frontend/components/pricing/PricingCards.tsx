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
 * $149/month verified-attorney subscription. An audience toggle (like
 * claude.com/pricing's Individual / Team switch) keeps each view to the
 * plans that actually apply to the visitor.
 */

type Audience = "citizens" | "attorneys";

type Plan = {
  id: string;
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  cta: string;
  href?: string;
  action?: "become-attorney";
  featured?: boolean;
  includes: string[];
};

const PLANS: Record<Audience, Plan[]> = {
  citizens: [
    {
      id: "free",
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
      name: "Full post",
      price: "$2.99",
      cadence: "one-time, per inquiry",
      blurb: "More room to explain and more evidence, for that one post.",
      cta: "Start an inquiry",
      href: "/inquiries/new",
      featured: true,
      includes: [
        "Everything in Free",
        "No 250-character limit",
        "Up to 5 files, 50 MB in total",
        "Pay only for the posts that need it",
        "Upgrade from the post itself, any time",
      ],
    },
  ],
  attorneys: [
    {
      id: "attorney",
      name: "Verified attorney",
      price: "$149",
      cadence: "per month",
      blurb: "Full access to the case feed and direct outreach to citizens who need help.",
      cta: "Apply as an attorney",
      action: "become-attorney",
      featured: true,
      includes: [
        "Full access to the comprehensive case ledger",
        "Send formal consultation requests on active inquiries",
        "Track all your client requests in one place",
        "Verified badge on the platform",
        "Subject to bar number and jurisdiction review",
      ],
    },
  ],
};

const COMPARISON: { feature: string; free: string | boolean; full: string | boolean }[] = [
  { feature: "Post length", free: "250 characters", full: "Unlimited" },
  { feature: "Files per post", free: "1", full: "Up to 5" },
  { feature: "File size", free: "5 MB", full: "50 MB total" },
  { feature: "Anonymous posting", free: true, full: true },
  { feature: "Edit or delete any time", free: true, full: true },
  { feature: "Follow inquiries", free: true, full: true },
];

function Cell({ value }: { value: string | boolean }) {
  if (value === true) return <Check className="mx-auto h-4 w-4 text-accent" aria-label="Included" />;
  if (value === false) return <Minus className="mx-auto h-4 w-4 text-text-muted" aria-label="Not included" />;
  return <span className="text-text-primary">{value}</span>;
}

export function PricingCards() {
  const { user, isLoading } = useUser();
  const [audience, setAudience] = useState<Audience>("citizens");
  const [attorneyDialogOpen, setAttorneyDialogOpen] = useState(false);
  const router = useRouter();
  const plans = PLANS[audience];

  const ctaClass = (featured?: boolean) =>
    `mt-6 block w-full rounded-lg px-4 py-3 text-center text-body-sm font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
      featured
        ? "bg-accent text-accent-foreground hover:bg-accent-hover"
        : "border border-border-strong text-text-primary hover:bg-bg-subtle"
    }`;

  return (
    <div className="mx-auto w-full max-w-[1000px]">
      <div className="flex justify-center">
        <div
          role="tablist"
          aria-label="Who is this for?"
          className="inline-flex rounded-full border border-border-default bg-bg-subtle p-1"
        >
          {(["citizens", "attorneys"] as const).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={audience === key}
              onClick={() => setAudience(key)}
              className={`rounded-full px-5 py-2 text-body-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-accent outline-none ${
                audience === key
                  ? "bg-bg-elevated text-text-primary shadow-card"
                  : "text-text-secondary hover:text-text-primary"
              }`}
            >
              {key === "citizens" ? "For citizens" : "For attorneys"}
            </button>
          ))}
        </div>
      </div>

      <div
        role="tabpanel"
        className={`mt-10 grid gap-6 ${plans.length > 1 ? "md:grid-cols-2" : "max-w-[480px] mx-auto"}`}
      >
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`flex flex-col rounded-2xl bg-bg-elevated p-7 sm:p-8 ${
              plan.featured ? "border-2 border-accent/60 shadow-card-lg" : "border border-border-default shadow-card"
            }`}
          >
            <h2 className="font-display text-h2 text-text-primary">{plan.name}</h2>
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

      {audience === "citizens" && (
        <div className="mt-16">
          <h2 className="font-display text-h2 text-text-primary text-center">Compare citizen plans</h2>
          <div className="mt-6 overflow-x-auto rounded-xl border border-border-default bg-bg-elevated">
            <table className="w-full min-w-[460px] border-collapse text-left text-body-sm">
              <thead>
                <tr className="border-b border-border-default bg-bg-subtle">
                  <th scope="col" className="px-5 py-3 font-medium text-text-secondary">
                    Feature
                  </th>
                  <th scope="col" className="px-5 py-3 text-center font-medium text-text-secondary">
                    Free
                  </th>
                  <th scope="col" className="px-5 py-3 text-center font-medium text-text-secondary">
                    Full post
                  </th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON.map((row) => (
                  <tr key={row.feature} className="border-b border-border-default last:border-0">
                    <th scope="row" className="px-5 py-3 font-normal text-text-primary">
                      {row.feature}
                    </th>
                    <td className="px-5 py-3 text-center">
                      <Cell value={row.free} />
                    </td>
                    <td className="px-5 py-3 text-center">
                      <Cell value={row.full} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <BecomeAttorneyDialog open={attorneyDialogOpen} onOpenChange={setAttorneyDialogOpen} />
    </div>
  );
}
