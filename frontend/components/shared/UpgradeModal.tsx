"use client";

import Link from "next/link";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getUpgradeReasonCopy } from "@/lib/upgradeReasons";
import { useUpgradeModalStore } from "@/stores/useUpgradeModalStore";

/**
 * Upgrade/paywall modal — AgentGuide/01_ThemeGuideline.md §4.7. Single
 * consumer of useUpgradeModalStore (built in Step 1, wired for real starting
 * Step 5) — any gated action anywhere in the app opens this same modal by
 * calling `useUpgradeModalStore.getState().open(reason)`. Step 7 extends the
 * contextual copy/plan comparison here; this is the real component, not a
 * throwaway placeholder.
 */
export function UpgradeModal() {
  const { isOpen, reason, close } = useUpgradeModalStore();
  const copy = getUpgradeReasonCopy(reason);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && close()}>
      <DialogContent className="bg-bg-elevated rounded-lg max-w-[420px]">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">{copy.title}</DialogTitle>
          <DialogDescription className="text-body-sm text-text-secondary">
            {copy.body}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2 mt-2">
          <Link
            href={`/upgrade${reason ? `?reason=${reason}` : ""}`}
            onClick={close}
            className="rounded-sm bg-accent px-4 py-2.5 text-center text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Upgrade to Pro
          </Link>
          <button
            type="button"
            onClick={close}
            className="rounded-sm px-4 py-2.5 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Maybe later
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
