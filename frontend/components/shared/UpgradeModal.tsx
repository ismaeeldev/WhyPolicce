"use client";

import { Check } from "lucide-react";
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

// UI polish pass: this was pure prose (title + one sentence + two buttons)
// at the exact moment meant to convert a free user — no visual
// reinforcement of what Pro actually includes. Mirrors the same 4 Pro-only
// lines from PricingCards.tsx's feature list so the two surfaces agree,
// without duplicating the full plan comparison inline.
const PRO_HIGHLIGHTS = [
  "Deep search — up to 50 intensive queries/day",
  "Advanced export — PDF, Markdown, bulk history",
  "Priority streaming during peak hours",
];

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

        <ul className="mt-1 flex flex-col gap-2 rounded-md border border-border-default bg-bg-subtle p-4">
          {PRO_HIGHLIGHTS.map((label) => (
            <li key={label} className="flex items-start gap-2.5 text-body-sm text-text-primary">
              <Check className="h-4 w-4 shrink-0 mt-0.5 text-accent-bright" />
              <span>{label}</span>
            </li>
          ))}
        </ul>

        <div className="flex flex-col gap-2 mt-4">
          <Link
            href={`/upgrade${reason ? `?reason=${reason}` : ""}`}
            onClick={close}
            className="rounded-sm bg-accent px-4 py-2.5 text-center text-body-sm font-medium text-accent-foreground transition-all hover:bg-accent-hover active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Upgrade to Pro — $12/month
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
