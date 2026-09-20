"use client";

import { motion } from "framer-motion";
import { Scale } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { AttorneyStatusBanner } from "@/components/account/AttorneyStatusBanner";
import { MyRequestsList } from "@/components/attorneys/MyRequestsList";
import { RequestConsultationButton } from "@/components/attorneys/RequestConsultationButton";
import { InquiryCard } from "@/components/feed/InquiryCard";
import { FeedEmptyStateNoInquiries } from "@/components/feed/FeedEmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { ATTORNEY_SUBSCRIPTION_ACTIVE_STUB } from "@/lib/attorneySubscription";
import { useInquiries, type Inquiry } from "@/hooks/useInquiries";
import { useUser } from "@/hooks/useUser";

const EASE = [0.22, 1, 0.36, 1] as const;
const DEFAULT_FEED_FILTERS = { region: "", status: "", sort: "newest" as const, q: "" };

/**
 * Attorney portal route guard — forum rebuild, Milestone 2 Steps M2.1
 * and M2.4 (WhyPoliceForum_MasterGuide.md). proxy.ts already enforces
 * authentication (redirects a logged-out visitor to /login); this page
 * adds the ROLE check on top — a citizen (or an attorney whose account
 * isn't role="attorney" yet) gets a real explanatory page, never a raw
 * API 403 or a silent 404 (per M2.1's own explicit requirement).
 *
 * Manual Step decision (M2.4, user-confirmed): an approved-but-not-yet-
 * subscribed attorney sees a real preview-then-paywall pattern — the
 * real feed, blurred, with a centered "$149/month" CTA — rather than a
 * hard redirect with zero preview. ATTORNEY_SUBSCRIPTION_ACTIVE_STUB is
 * a deliberately named, always-false placeholder (see
 * lib/attorneySubscription.ts's own docstring) pending Milestone 3's
 * real Stripe subscription wiring — never a fake always-true value.
 */
export default function AttorneyDashboardPage() {
  const { data: me, isLoading } = useUser();

  if (isLoading) {
    return (
      <div className="mx-auto w-full max-w-[720px] px-5 sm:px-6 py-16 sm:py-20">
        <Skeleton className="h-9 w-64 mb-8" />
        <Skeleton className="h-24 w-full rounded-md" />
      </div>
    );
  }

  if (me?.role !== "attorney") {
    return (
      <div className="mx-auto flex w-full max-w-[560px] flex-1 flex-col items-center justify-center px-5 sm:px-6 py-24 text-center">
        <Scale className="h-10 w-10 text-text-muted mb-6" strokeWidth={1.5} />
        <h1 className="font-display text-h1 mb-3">This is the attorney portal.</h1>
        <p className="max-w-sm text-body text-text-secondary mb-8">
          Only verified attorney accounts can access this page. If you&apos;re a licensed
          attorney, you can apply from your account page.
        </p>
        <Link
          href="/account"
          className="rounded-sm bg-accent px-5 py-2.5 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Go to Account
        </Link>
      </div>
    );
  }

  if (me.verificationStatus !== "approved") {
    return (
      <div className="mx-auto w-full max-w-[560px] px-5 sm:px-6 py-16 sm:py-20">
        <motion.h1
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: EASE }}
          className="font-display text-h1 mb-6"
        >
          Attorney Portal
        </motion.h1>
        <AttorneyStatusBanner status={me.verificationStatus ?? "pending"} />
      </div>
    );
  }

  return <ApprovedAttorneyPortal />;
}

function ApprovedAttorneyPortal() {
  const [showingRequests, setShowingRequests] = useState(false);
  const feedQuery = useInquiries(DEFAULT_FEED_FILTERS);
  const items = feedQuery.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="mx-auto w-full max-w-[1200px] px-5 sm:px-6 py-8 sm:py-12">
      <div className="mx-auto max-w-[760px]">
        <div className="mb-6 flex items-center justify-between gap-3">
          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="font-display text-h1"
          >
            Attorney Portal
          </motion.h1>
          <button
            type="button"
            onClick={() => setShowingRequests((v) => !v)}
            className="rounded-sm border border-border-default px-3.5 py-2 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            {showingRequests ? "Back to cases" : "My Requests"}
          </button>
        </div>

        {showingRequests ? (
          <MyRequestsList />
        ) : (
          <AttorneyCaseFeed subscribed={ATTORNEY_SUBSCRIPTION_ACTIVE_STUB} items={items} isLoading={feedQuery.isLoading} />
        )}
      </div>
    </div>
  );
}

function AttorneyCaseFeed({
  subscribed,
  items,
  isLoading,
}: {
  subscribed: boolean;
  items: Inquiry[];
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-32 animate-pulse rounded-md border border-border-default bg-bg-elevated" />
        ))}
      </div>
    );
  }

  if (!subscribed) {
    return (
      <div className="relative">
        <div aria-hidden="true" className="pointer-events-none blur-sm select-none opacity-60">
          <div className="flex flex-col gap-4">
            {items.slice(0, 3).map((inquiry) => (
              <InquiryCard key={inquiry.id} inquiry={inquiry} />
            ))}
            {items.length === 0 && <FeedEmptyStateNoInquiries />}
          </div>
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 rounded-md border border-border-default bg-bg-elevated p-8 text-center shadow-card">
            <p className="text-body font-medium text-text-primary">Subscribe to see real cases</p>
            <p className="max-w-xs text-body-sm text-text-secondary">
              A $149/month subscription gives you full access to every inquiry and lets you
              request consultations directly.
            </p>
            {/* TODO (Milestone 3, Step M3.x): wire to a real Stripe
                Checkout session for the $149/month attorney
                subscription. Deliberately a placeholder, not a fake
                success state. */}
            <button
              type="button"
              className="mt-1 rounded-sm bg-accent px-5 py-2.5 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
            >
              Subscribe for $149/month
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return <FeedEmptyStateNoInquiries />;
  }

  return (
    <div className="flex flex-col gap-4">
      {items.map((inquiry) => (
        <InquiryCard
          key={inquiry.id}
          inquiry={inquiry}
          extraAction={<RequestConsultationButton inquiryId={inquiry.id} />}
        />
      ))}
    </div>
  );
}
