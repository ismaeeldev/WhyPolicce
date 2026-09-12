"use client";

import { useUser as useAuth0User } from "@auth0/nextjs-auth0";
import { motion } from "framer-motion";
import { BrainCircuit, ChevronRight, CreditCard, Sparkles } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useUser } from "@/hooks/useUser";
import { useToastStore } from "@/stores/useToastStore";

const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Account page — AgentGuide/02_ApplicationFlow.md §3.6: profile info (from
 * Auth0), current tier badge, a "Manage billing" entry point, a link to
 * Memory, logout. Brought up to the same visual bar as History/Memory
 * (Steps 6/6.5) during a UI modernization pass — a page heading, staggered
 * entrance motion, and a real card treatment (hover lift + shadow) instead
 * of a flat bordered box, none of which this page had before.
 */
export default function AccountPage() {
  const { user: auth0User } = useAuth0User();
  const { data: me, refetch } = useUser();
  const searchParams = useSearchParams();
  const showToast = useToastStore((s) => s.show);

  useEffect(() => {
    if (searchParams.get("upgraded") !== "1") return;
    void refetch();
    showToast("Welcome to Pro — your plan is now active.");
    window.history.replaceState({}, "", "/account");
  }, [searchParams, refetch, showToast]);

  const tier = me?.tier ?? "free";

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
          <p className="text-body-sm text-text-muted truncate">{auth0User?.email}</p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1, ease: EASE }}
                className="mt-6 rounded-md border border-border-default bg-bg-elevated p-5 sm:p-6 shadow-card transition-shadow duration-150 hover:shadow-card"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-body-sm text-text-secondary">Current plan</p>
            <span
              className={`mt-1.5 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-caption font-medium ${
                tier === "pro"
                  ? "bg-accent-subtle text-text-primary"
                  : "bg-bg-subtle text-text-secondary"
              }`}
            >
              {tier === "pro" && <Sparkles className="h-3 w-3 text-accent-bright" />}
              {tier === "pro" ? "Pro" : "Free"}
            </span>
          </div>
          {tier !== "pro" && (
            <Link
              href="/upgrade"
              className="rounded-sm bg-accent px-3.5 py-2 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
            >
              Upgrade
            </Link>
          )}
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.15, ease: EASE }}
        className="mt-3 flex flex-col gap-2"
      >
        <Link
          href="/account/billing"
          className="group flex items-center gap-2.5 rounded-sm border border-border-default px-4 py-3 text-body-sm text-text-primary transition-colors hover:border-border-strong hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          <CreditCard className="h-4 w-4 text-text-muted" />
          Manage billing
          <ChevronRight className="ml-auto h-4 w-4 text-text-muted transition-transform group-hover:translate-x-0.5" />
        </Link>
        <Link
          href="/account/memory"
          className="group flex items-center gap-2.5 rounded-sm border border-border-default px-4 py-3 text-body-sm text-text-primary transition-colors hover:border-border-strong hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          <BrainCircuit className="h-4 w-4 text-text-muted" />
          Memory
          <ChevronRight className="ml-auto h-4 w-4 text-text-muted transition-transform group-hover:translate-x-0.5" />
        </Link>
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
    </div>
  );
}
