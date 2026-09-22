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
  title = "This post needs the $2.99 upgrade",
  description = `Free posts are capped at ${FREE_TIER_CHAR_LIMIT} characters. Trim it down to keep posting for free — you can upgrade to publish the full text once it's posted.`,
  secondaryAction,
  primaryAction,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTrimInstead?: () => void;
  descriptionTextareaRef?: React.RefObject<HTMLTextAreaElement | null>;
  title?: string;
  description?: string;
  // M3.1: the attachment-limit trigger has no "trim it down" equivalent
  // (there's no partial file to shrink), so the secondary action's label
  // is overridable — same modal shell/interaction pattern per the guide's
  // own "should feel like the same product mechanism" requirement,
  // without forcing copy that doesn't make sense for this trigger.
  secondaryAction?: { label: string; onClick: () => void };
  // M3.2 real fix: the create-inquiry flow has no real inquiry_id yet to
  // check out against (payment only ever applies to an inquiry that
  // already exists — see the backend's own tier=free-only enforcement),
  // so that specific modal instance has no real "Upgrade for $2.99"
  // action to offer. Only a caller with a real, already-created inquiry
  // (the post-creation upgrade path) passes this to wire the real
  // Stripe Checkout call; omitting it hides the primary button entirely
  // rather than showing a dead placeholder.
  primaryAction?: { label: string; onClick: () => void; isPending?: boolean };
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-bg-elevated rounded-lg max-w-[420px]"
        finalFocus={descriptionTextareaRef}
      >
        <DialogHeader>
          <DialogTitle className="font-display text-2xl">{title}</DialogTitle>
          <DialogDescription className="text-body-sm text-text-secondary">
            {description}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2 mt-4">
          {primaryAction && (
            <button
              type="button"
              onClick={primaryAction.onClick}
              disabled={primaryAction.isPending}
              className="rounded-sm bg-accent px-4 py-2.5 text-center text-body-sm font-medium text-accent-foreground transition-all hover:bg-accent-hover active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
            >
              {primaryAction.isPending ? "Redirecting…" : primaryAction.label}
            </button>
          )}
          {(secondaryAction ?? onTrimInstead) && (
            <button
              type="button"
              onClick={() => {
                if (secondaryAction) {
                  secondaryAction.onClick();
                } else {
                  onTrimInstead?.();
                }
                onOpenChange(false);
              }}
              className="rounded-sm px-4 py-2.5 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
            >
              {secondaryAction?.label ?? "Trim my post instead"}
            </button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
