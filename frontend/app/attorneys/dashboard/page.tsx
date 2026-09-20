"use client";

import { motion } from "framer-motion";
import { Scale } from "lucide-react";
import Link from "next/link";

import { AttorneyStatusBanner } from "@/components/account/AttorneyStatusBanner";
import { Skeleton } from "@/components/ui/skeleton";
import { useUser } from "@/hooks/useUser";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Attorney portal route guard — forum rebuild, Milestone 2 Step M2.1
 * (WhyPoliceForum_MasterGuide.md). proxy.ts already enforces
 * authentication (redirects a logged-out visitor to /login); this page
 * adds the ROLE check on top — a citizen (or an attorney whose account
 * isn't role="attorney" yet) gets a real explanatory page, never a raw
 * API 403 or a silent 404 (per this step's own explicit requirement).
 * The real portal UI itself is built in M2.4 — this is deliberately a
 * placeholder for an approved attorney, just enough to prove the guard
 * itself passes them through correctly.
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

  return (
    <div className="mx-auto w-full max-w-[720px] px-5 sm:px-6 py-16 sm:py-20">
      <motion.h1
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: EASE }}
        className="font-display text-h1 mb-3"
      >
        Attorney Portal
      </motion.h1>
      <p className="text-body text-text-secondary">
        Full portal coming in Milestone 2 Step M2.4 — your account is verified and this route
        guard is working correctly.
      </p>
    </div>
  );
}
