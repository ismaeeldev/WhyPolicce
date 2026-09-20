"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const FREE_TIER_CHAR_LIMIT = 250;

/**
 * $2.99 upgrade modal — forum rebuild, Milestone 2 Step M2.3
 * (WhyPoliceForum_MasterGuide.md). Matches the real shipped
 * UpgradeModal.tsx's actual conventions, not ThemeGuideline §4.7's
 * stale prose where the two diverge: that component has no Framer
 * Motion of its own (the entrance animation is base-ui's own CSS
 * data-open/data-closed classes on dialog.tsx, 100ms) and dialog.tsx's
 * real z-index is z-50, not the doc's z-[60] — this modal inherits
 * both from the same shared Dialog primitive rather than reinventing
 * a second animation/stacking approach for one screen.
 *
 * Real, deliberate difference from UpgradeModal.tsx: THIS modal is
 * opened by local form state (an onSubmit intercept), not a
 * Dialog.Trigger, so base-ui's automatic return-focus-to-trigger has
 * no real trigger element to return to. M2.3's own spec requires focus
 * landing on a SPECIFIC element (the description textarea) on close —
 * handled explicitly via the underlying @base-ui/react Dialog.Popup's
 * own `finalFocus` prop (a real base-ui API, not Radix's
 * onCloseAutoFocus event-callback convention, which this primitive
 * doesn't have) rather than relying on the trigger-based default.
 */
export function UpgradeModal({
  open,
  onOpenChange,
  onTrimInstead,
  descriptionTextareaRef,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTrimInstead: () => void;
  descriptionTextareaRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-bg-elevated rounded-lg max-w-[420px]"
        finalFocus={descriptionTextareaRef}
      >
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">
            This post needs the $2.99 upgrade
          </DialogTitle>
          <DialogDescription className="text-body-sm text-text-secondary">
            Free posts are capped at {FREE_TIER_CHAR_LIMIT} characters. Upgrade this post to
            publish the full text, or trim it down and keep posting for free.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2 mt-4">
          <button
            type="button"
            onClick={() => {
              // TODO (Milestone 3, Step M3.2): wire this to a real Stripe
              // Checkout session for the $2.99 one-time upgrade. This is
              // deliberately a placeholder, not a fake success state —
              // per M2.3's own explicit requirement not to build
              // something that could be mistaken for real payment
              // integration.
            }}
            className="rounded-sm bg-accent px-4 py-2.5 text-center text-body-sm font-medium text-accent-foreground transition-all hover:bg-accent-hover active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Upgrade for $2.99
          </button>
          <button
            type="button"
            onClick={() => {
              onTrimInstead();
              onOpenChange(false);
            }}
            className="rounded-sm px-4 py-2.5 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Trim my post instead
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
