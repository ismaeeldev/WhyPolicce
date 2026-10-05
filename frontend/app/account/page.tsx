"use client";

import { useUser as useAuth0User } from "@auth0/nextjs-auth0";
import { motion } from "framer-motion";
import { ChevronRight, FileText, Scale, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AttorneyStatusBanner } from "@/components/account/AttorneyStatusBanner";
import { BecomeAttorneyDialog } from "@/components/account/BecomeAttorneyDialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { useUser } from "@/hooks/useUser";
import { useToastStore } from "@/stores/useToastStore";

const EASE = [0.22, 1, 0.36, 1] as const;

export default function AccountPage() {
  const { user: auth0User } = useAuth0User();
  const { data: me, isLoading: meLoading, isError: meError, refetch: refetchMe } = useUser();
  const [attorneyDialogOpen, setAttorneyDialogOpen] = useState(false);
  const searchParams = useSearchParams();
  const showToast = useToastStore((s) => s.show);

  useEffect(() => {
    if (searchParams.get("upgraded") !== "1") return;
    void refetchMe();
    showToast("You're upgraded — thanks for subscribing.");
    window.history.replaceState({}, "", "/account");
  }, [searchParams, refetchMe, showToast]);

  return (
    <div className="mx-auto w-full min-w-0 max-w-[620px] px-5 sm:px-6 py-12 sm:py-16">
      <div className="mb-8">
        <h1 className="font-display text-h1 text-text-primary tracking-tight">Account &amp; Settings</h1>
        <p className="mt-1 text-body-sm text-text-secondary">
          Manage your forum presence, credentials, and role status.
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05, ease: EASE }}
        className="rounded-2xl border border-border-default/80 bg-bg-elevated/90 p-5 sm:p-6 backdrop-blur-sm shadow-card flex min-w-0 items-center gap-4"
      >
        <Avatar className="size-16 shrink-0 ring-2 ring-accent/30 ring-offset-2 ring-offset-bg">
          <AvatarImage src={auth0User?.picture} alt={auth0User?.name ?? "Account"} />
          <AvatarFallback className="text-xl font-serif bg-accent-subtle text-accent-bright">
            {(auth0User?.name ?? auth0User?.email ?? "?").charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-body font-semibold text-text-primary truncate">
              {auth0User?.name ?? auth0User?.email}
            </p>
            {me?.role === "attorney" && me.verificationStatus === "approved" && (
              <span className="inline-flex items-center gap-1 rounded-full bg-accent/15 px-2 py-0.5 text-caption font-medium text-accent-bright border border-accent/30">
                <ShieldCheck className="h-3 w-3" />
                <span>Verified Attorney</span>
              </span>
            )}
          </div>
          {auth0User?.email && auth0User.email !== auth0User?.name && (
            <p className="text-body-sm text-text-muted truncate mt-0.5">{auth0User.email}</p>
          )}
        </div>
      </motion.div>

      {/* Account Navigation / Quick links */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1, ease: EASE }}
        className="mt-6 flex flex-col gap-3"
      >
        <Link
          href="/account/my-inquiries"
          className="group flex items-center justify-between rounded-xl border border-border-default/80 bg-bg-elevated p-4 transition-all duration-200 hover:border-accent/40 hover:bg-bg-subtle hover:shadow-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-subtle/50 text-accent">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <p className="text-body-sm font-semibold text-text-primary">My Inquiries</p>
              <p className="text-caption text-text-muted">View and manage the inquiries you have created</p>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-text-muted transition-transform group-hover:translate-x-1" />
        </Link>

        {me?.role === "attorney" && (
          <Link
            href="/attorneys/dashboard"
            className="group flex items-center justify-between rounded-xl border border-border-default/80 bg-bg-elevated p-4 transition-all duration-200 hover:border-accent/40 hover:bg-bg-subtle hover:shadow-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/20 text-accent-bright">
                <Scale className="h-5 w-5" />
              </div>
              <div>
                <p className="text-body-sm font-semibold text-text-primary">Attorney Portal &amp; Cases</p>
                <p className="text-caption text-text-muted">Review public cases and manage consultation requests</p>
              </div>
            </div>
            <ChevronRight className="h-4 w-4 text-text-muted transition-transform group-hover:translate-x-1" />
          </Link>
        )}
      </motion.div>

      {/* Attorney entry point */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.15, ease: EASE }}
        className="mt-6"
      >
        {meLoading ? (
          <Skeleton className="h-[56px] w-full rounded-xl" />
        ) : meError ? (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-border-default bg-bg-subtle px-4 py-3.5">
            <p className="text-body-sm text-text-secondary">Couldn&apos;t load verification status.</p>
            <button
              type="button"
              onClick={() => refetchMe()}
              className="shrink-0 text-body-sm font-semibold text-accent hover:text-accent-hover transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
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
            className="group flex w-full items-center gap-3 rounded-xl border border-border-default/80 bg-bg-elevated p-4 text-left transition-all duration-200 hover:border-accent/40 hover:bg-bg-subtle hover:shadow-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-subtle/50 text-accent">
              <Scale className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <p className="text-body-sm font-semibold text-text-primary">Apply as Verified Attorney</p>
              <p className="text-caption text-text-muted">Unlock case consultation requests and outreach features</p>
            </div>
            <ChevronRight className="h-4 w-4 text-text-muted transition-transform group-hover:translate-x-1" />
          </button>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.2, ease: EASE }}
        className="mt-10 border-t border-border-default/60 pt-6 flex justify-center"
      >
        <a
          href="/auth/logout"
          className="inline-flex items-center justify-center rounded-xl border border-border-default px-6 py-2.5 text-body-sm font-medium text-text-muted hover:text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Sign out of account
        </a>
      </motion.div>

      <BecomeAttorneyDialog open={attorneyDialogOpen} onOpenChange={setAttorneyDialogOpen} />
    </div>
  );
}
