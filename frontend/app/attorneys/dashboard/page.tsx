"use client";

import { motion } from "framer-motion";
import { Scale } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AttorneyStatusBanner } from "@/components/account/AttorneyStatusBanner";
import { MyRequestsList } from "@/components/attorneys/MyRequestsList";
import { RequestConsultationButton } from "@/components/attorneys/RequestConsultationButton";
import { InquiryCard } from "@/components/feed/InquiryCard";
import { FeedEmptyStateNoInquiries } from "@/components/feed/FeedEmptyState";
import { ListPageSkeleton } from "@/components/shared/ListPageSkeleton";
import { Skeleton } from "@/components/ui/skeleton";
import { useAttorneySubscriptionCheckout } from "@/hooks/useForumBilling";
import { useInquiries, type Inquiry } from "@/hooks/useInquiries";
import { useUser } from "@/hooks/useUser";
import { useToastStore } from "@/stores/useToastStore";

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
 * hard redirect with zero preview. `subscribed` now reads the real,
 * webhook-confirmed `attorneySubscriptionActive` field from GET /api/me
 * (Milestone 3 Step M3.2), replacing the M2.4-era
 * ATTORNEY_SUBSCRIPTION_ACTIVE_STUB placeholder now that real payment
 * exists to back it.
 */
export default function AttorneyDashboardPage() {
  const { data: me, isLoading, isError: meError, refetch } = useUser();
  const searchParams = useSearchParams();
  const showToast = useToastStore((s) => s.show);

  // Real M3.2 post-checkout return handling — same ?param=1 + refetch +
  // toast + clean-URL pattern established by the old AccountPage's own
  // post-checkout handling and the thread page's ?upgraded=1 above.
  useEffect(() => {
    if (searchParams.get("subscribed") !== "1") return;
    void refetch();
    showToast("Subscription active — you now have full portal access.");
    window.history.replaceState({}, "", "/attorneys/dashboard");
  }, [searchParams, refetch, showToast]);

  if (isLoading) return <ListPageSkeleton />;

  if (meError) {
    // Real bug found during a state-handling audit: isError was never
    // read here, so ANY /api/me failure (useUser's own retry: 1 means
    // this triggers after just two failed attempts) fell through to
    // `me?.role !== "attorney"` (undefined !== "attorney" is true) and
    // told a real, verified attorney that only verified attorneys can
    // access this page — the exact account it's talking to.
    return (
      <div className="mx-auto flex w-full max-w-[560px] flex-1 flex-col items-center justify-center px-5 sm:px-6 py-24 text-center">
        <Scale className="h-10 w-10 text-text-muted mb-6" strokeWidth={1.5} />
        <h1 className="font-display text-h1 mb-3">Couldn&apos;t load your account.</h1>
        <p className="max-w-sm text-body text-text-secondary mb-8">That&apos;s on us, not you — try again.</p>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-sm bg-accent px-5 py-2.5 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Try again
        </button>
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

  return <ApprovedAttorneyPortal subscribed={me.attorneySubscriptionActive} />;
}

function ApprovedAttorneyPortal({ subscribed }: { subscribed: boolean }) {
  const [showingRequests, setShowingRequests] = useState(false);
  const feedQuery = useInquiries(DEFAULT_FEED_FILTERS);
  const items = feedQuery.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="mx-auto w-full max-w-[1200px] px-5 sm:px-6 py-8 sm:py-12">
      <div className="mx-auto max-w-[760px]">
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-default/60 pb-6">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/20 bg-accent-subtle/50 px-3 py-0.5 text-caption font-medium text-accent-bright mb-2">
              <Scale className="h-3.5 w-3.5 text-accent" />
              <span>Attorney Console</span>
            </div>
            <motion.h1
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: EASE }}
              className="font-display text-h1 text-text-primary tracking-tight"
            >
              Attorney Portal
            </motion.h1>
            <p className="mt-1 text-body-sm text-text-secondary">
              Review active jurisdiction cases and initiate direct citizen consultations.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowingRequests((v) => !v)}
            className="rounded-xl border border-border-default/90 bg-bg-elevated px-4 py-2.5 text-body-sm font-semibold text-text-primary hover:border-accent/40 hover:bg-bg-subtle transition-all duration-200 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none shadow-sm"
          >
            {showingRequests ? "← Back to Case Feed" : "My Consultations"}
          </button>
        </div>

        {showingRequests ? (
          <MyRequestsList />
        ) : (
          <AttorneyCaseFeed
            subscribed={subscribed}
            items={items}
            isLoading={feedQuery.isLoading}
            isError={feedQuery.isError}
            onRetry={() => feedQuery.refetch()}
          />
        )}
      </div>
    </div>
  );
}

function AttorneyCaseFeed({
  subscribed,
  items,
  isLoading,
  isError,
  onRetry,
}: {
  subscribed: boolean;
  items: Inquiry[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-36 w-full rounded-2xl" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-2xl border border-danger/40 bg-danger-subtle p-6 text-center shadow-sm">
        <p className="text-body-sm text-text-primary mb-3">The case feed didn&apos;t load.</p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-xl bg-accent px-4 py-2 text-body-sm font-semibold text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!subscribed) {
    return (
      <div className="relative">
        <div aria-hidden="true" className="pointer-events-none blur-sm select-none opacity-50">
          <div className="flex flex-col gap-4">
            {items.slice(0, 3).map((inquiry) => (
              <InquiryCard key={inquiry.id} inquiry={inquiry} />
            ))}
            {items.length === 0 && <FeedEmptyStateNoInquiries />}
          </div>
        </div>
        <div className="absolute inset-0 flex items-center justify-center px-4">
          <div className="flex w-[min(380px,100%)] flex-col items-center gap-3.5 rounded-2xl border-2 border-accent/40 bg-bg-elevated/95 p-6 sm:p-8 text-center shadow-2xl backdrop-blur-md">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/15 text-accent-bright ring-1 ring-accent/30">
              <Scale className="h-6 w-6" />
            </div>
            <p className="text-h3 font-serif font-semibold text-text-primary">Subscribe to Access Real Cases</p>
            <p className="max-w-xs text-body-sm text-text-secondary leading-relaxed">
              A $149/month subscription gives you full unredacted access to every community inquiry and direct client consultation outreach.
            </p>
            <SubscribeButton />
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
          extraAction={
            <RequestConsultationButton
              inquiryId={inquiry.id}
              serverStatus={inquiry.myRequestStatus ?? null}
            />
          }
        />
      ))}
    </div>
  );
}

function SubscribeButton() {
  const checkout = useAttorneySubscriptionCheckout();
  return (
    <button
      type="button"
      onClick={() => checkout.mutate()}
      disabled={checkout.isPending}
      className="mt-2 w-full rounded-xl bg-accent px-5 py-3 text-body-sm font-semibold text-accent-foreground hover:bg-accent-hover hover:shadow-md disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-200 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
    >
      {checkout.isPending ? "Redirecting to Stripe…" : "Subscribe for $149/month"}
    </button>
  );
}
