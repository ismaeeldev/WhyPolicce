"use client";

import { useUser as useAuth0User } from "@auth0/nextjs-auth0";
import { motion } from "framer-motion";
import { ChevronRight, Scale } from "lucide-react";
import { useState } from "react";

import { AttorneyStatusBanner } from "@/components/account/AttorneyStatusBanner";
import { BecomeAttorneyDialog } from "@/components/account/BecomeAttorneyDialog";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useUser } from "@/hooks/useUser";

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
  const { data: me } = useUser();
  const [attorneyDialogOpen, setAttorneyDialogOpen] = useState(false);

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

      {/* Forum rebuild M2.1: attorney entry point. role/verificationStatus
          ride the same /api/me request as tier above (no second loading
          state), matching this step's own explicit requirement. */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1, ease: EASE }}
        className="mt-8"
      >
        {me?.role === "attorney" && me.verificationStatus ? (
          <AttorneyStatusBanner status={me.verificationStatus} />
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
