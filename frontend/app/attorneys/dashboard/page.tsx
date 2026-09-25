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

  if (isLoading) {
    return (
      <div className="mx-auto w-full max-w-[720px] px-5 sm:px-6 py-16 sm:py-20">
        <Skeleton className="h-9 w-64 mb-8" />
        <Skeleton className="h-24 w-full rounded-md" />
      </div>
    );
  }

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
          <Skeleton key={i} className="h-32 w-full rounded-md" />
        ))}
      </div>
    );
  }

  if (isError) {
    // Real bug found during a state-handling audit: this component only
    // ever destructured `data`/`isLoading`, so a failed feed fetch fell
    // through with `items` defaulting to [] and rendered the SAME empty
    // state as "the forum genuinely has zero inquiries" — a $149/month
    // attorney hitting an API blip was told the product has no content,
    // with no way to retry. Worse, this false-empty rendered blurred
    // behind the subscribe paywall for an unsubscribed attorney,
    // making the product look empty right as it's trying to sell them
    // on subscribing to it.
    return (
      <div className="rounded-md border border-danger bg-danger-subtle p-5 text-center">
        <p className="text-body-sm text-text-primary mb-3">The case feed didn&apos;t load.</p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-sm px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Try again
        </button>
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
        <div className="absolute inset-0 flex items-center justify-center px-4">
          <div className="flex w-[min(320px,100%)] flex-col items-center gap-3 rounded-md border border-accent/30 bg-bg-elevated p-6 sm:p-8 text-center shadow-card-lg">
            <p className="text-body font-medium text-text-primary">Subscribe to see real cases</p>
            <p className="max-w-xs text-body-sm text-text-secondary">
              A $149/month subscription gives you full access to every inquiry and lets you
              request consultations directly.
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
      className="mt-1 rounded-sm bg-accent px-5 py-2.5 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover disabled:opacity-60 disabled:cursor-not-allowed transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
    >
      {checkout.isPending ? "Redirecting…" : "Subscribe for $149/month"}
    </button>
  );
}
