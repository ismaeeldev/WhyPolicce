"use client";

import { useUser as useAuth0User } from "@auth0/nextjs-auth0";
import { motion } from "framer-motion";
import { ChevronRight, Scale } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AttorneyStatusBanner } from "@/components/account/AttorneyStatusBanner";
import { BecomeAttorneyDialog } from "@/components/account/BecomeAttorneyDialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { useUser } from "@/hooks/useUser";
import { useToastStore } from "@/stores/useToastStore";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Account page — forum rebuild. Profile info (from Auth0), the
 * "Become an Attorney" entry point, logout. The old RAG-search
 * product's "Current plan"/"Manage billing"/Memory links are
 * deliberately removed here: that Free/Pro subscription concept and
 * the Memory feature are both retired per the scope PDF's own "What
 * We Are No Longer Building On" section — showing them on a real
 * forum user's Account page would describe a product that no longer
 * exists. The forum's own separate monetization (per-inquiry $2.99,
 * attorney $149/month) lives on the inquiry thread page and the
 * attorney portal respectively, not here.
 */
export default function AccountPage() {
  const { user: auth0User } = useAuth0User();
  const { data: me, isLoading: meLoading, isError: meError, refetch: refetchMe } = useUser();
  const [attorneyDialogOpen, setAttorneyDialogOpen] = useState(false);
  const searchParams = useSearchParams();
  const showToast = useToastStore((s) => s.show);

  // Stripe checkout success redirect (backend/app/routers/billing.py's
  // success_url) — without this, a user returning from a successful
  // upgrade sees stale (pre-upgrade) tier data until the cache naturally
  // refetches, since the webhook that actually flips their tier can land
  // slightly after the redirect. Same ?param=1 + refetch + toast +
  // clean-URL pattern as /attorneys/dashboard's ?subscribed=1 handling.
  useEffect(() => {
    if (searchParams.get("upgraded") !== "1") return;
    void refetchMe();
    showToast("You're upgraded — thanks for subscribing.");
    window.history.replaceState({}, "", "/account");
  }, [searchParams, refetchMe, showToast]);

  return (
    <div className="mx-auto w-full min-w-0 max-w-[560px] px-5 sm:px-6 py-16 sm:py-20">
      <motion.h1
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: EASE }}
        className="font-display text-h1 text-text-primary mb-8"
      >
        Account
      </motion.h1>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05, ease: EASE }}
        className="flex min-w-0 items-center gap-4"
      >
        <Avatar className="size-16 shrink-0 ring-2 ring-border-default ring-offset-2 ring-offset-bg">
          <AvatarImage src={auth0User?.picture} alt={auth0User?.name ?? "Account"} />
          <AvatarFallback className="text-lg bg-accent-subtle text-text-primary">
            {(auth0User?.name ?? auth0User?.email ?? "?").charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="text-body font-medium text-text-primary truncate">
            {auth0User?.name ?? auth0User?.email}
          </p>
          {/* Real bug found during a UI audit: Auth0 defaults `name` to
              the email itself when a user never sets a separate display
              name (true for most real accounts, which just sign up with
              email/password) — showing the muted email line unconditionally
              then just repeated the exact same truncated string twice.
              Only show it when it's genuinely a distinct value. */}
          {auth0User?.email && auth0User.email !== auth0User?.name && (
            <p className="text-body-sm text-text-muted truncate">{auth0User.email}</p>
          )}
        </div>
      </motion.div>

      {/* Forum rebuild M2.1: attorney entry point. role/verificationStatus
          ride the same /api/me request as tier above (no second loading
          state), matching this step's own explicit requirement. */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1, ease: EASE }}
        className="mt-8"
      >
        {meLoading ? (
          // Real bug found during a full-scope re-audit: this block used
          // to render straight off `me?.role`/`me.verificationStatus`
          // with no isLoading check, so while /api/me was still in
          // flight the `?.` short-circuit always fell through to the
          // "Become an Attorney" CTA — even for an ALREADY approved or
          // rejected attorney. That button opens a dialog wired to a
          // mutation the backend guarantees will 400 for that exact
          // account state (users.py's already_decided check), so an
          // approved attorney on a cold cache could open the dialog,
          // fill it in, and get told their application was "already
          // decided" — right as the real banner silently swapped in
          // behind it. useUser() already exposes a correct composite
          // isLoading; the attorney dashboard page already uses this
          // same skeleton-while-loading pattern, this page just hadn't
          // applied it.
          <Skeleton className="h-[52px] w-full rounded-sm" />
        ) : meError ? (
          // Real gap found during a state-handling audit, same class as
          // the loading-state fix above but for the error case: isError
          // was still unread, so a failed /api/me left `me` undefined
          // and fell through to the SAME "Become an Attorney" CTA —
          // including for an already-approved/rejected attorney, who
          // could open the dialog and hit the exact already_decided 400
          // the loading-state fix above was written to prevent.
          <div className="flex items-center justify-between gap-3 rounded-sm border border-border-default bg-bg-subtle px-4 py-3">
            <p className="text-body-sm text-text-secondary">Couldn&apos;t load this section.</p>
            <button
              type="button"
              onClick={() => refetchMe()}
              className="shrink-0 text-body-sm font-medium text-accent hover:text-accent-hover transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
            >
              Try again
            </button>
          </div>
        ) : me?.role === "attorney" && me.verificationStatus ? (
          <AttorneyStatusBanner
            status={me.verificationStatus}
            onReapplyClick={
              me.verificationStatus === "rejected" ? () => setAttorneyDialogOpen(true) : undefined
            }
          />
        ) : (
          <button
            type="button"
            onClick={() => setAttorneyDialogOpen(true)}
            className="group flex w-full items-center gap-2.5 rounded-sm border border-border-default px-4 py-3 text-body-sm text-text-primary transition-colors hover:border-border-strong hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            <Scale className="h-4 w-4 text-text-muted" />
            Become an Attorney
            <ChevronRight className="ml-auto h-4 w-4 text-text-muted transition-transform group-hover:translate-x-0.5" />
          </button>
        )}
      </motion.div>

      <motion.a
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.2, ease: EASE }}
        href="/auth/logout"
        className="mt-8 block text-center text-body-sm text-text-muted hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm"
      >
        Log out
      </motion.a>

      <BecomeAttorneyDialog open={attorneyDialogOpen} onOpenChange={setAttorneyDialogOpen} />
    </div>
  );
}
