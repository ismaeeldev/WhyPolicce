"use client";

import { useRef, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useBecomeAttorney } from "@/hooks/useBecomeAttorney";

/**
 * "Become an Attorney" form — AgentGuide/01_ThemeGuideline.md §4.8 (stacked
 * labels, --bg-elevated inputs, --danger inline errors with reserved
 * space). Same one-dialog-does-add pattern as memory/NoteFormDialog.tsx.
 */
export function BecomeAttorneyDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [barNo, setBarNo] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [touched, setTouched] = useState(false);
  const mutation = useBecomeAttorney();
  // Real gap found during a state-handling audit: disabled={isPending}
  // alone doesn't close the synchronous double-click window — React
  // state updates aren't synchronous, so two rapid clicks can both fire
  // mutate() before the first render reflecting isPending=true commits.
  // This mutation changes the account's role, so a duplicate POST is
  // more consequential than most; app/inquiries/new/page.tsx already
  // established this exact ref-lock pattern for the same reason.
  const submitLockRef = useRef(false);

  // Radix keeps DialogContent mounted (just hidden) across open/close, so
  // this component never remounts — without resetting here, closing after
  // a failed or partially-filled submission and reopening later shows
  // stale input/error state instead of a fresh form. Routed through this
  // wrapper (not a useEffect on `open`) since both the Cancel button and
  // Radix's own close paths (Escape, overlay click) call onOpenChange.
  const handleOpenChange = (next: boolean) => {
    // Block close while a submit is in-flight (Escape/overlay-click can
    // still fire onOpenChange even with the buttons disabled) — closing
    // here would reset state out from under the pending mutation, whose
    // onSuccess/onError would then fire against an already-reset dialog.
    if (!next && mutation.isPending) return;
    if (!next) {
      setBarNo("");
      setJurisdiction("");
      setTouched(false);
      submitLockRef.current = false;
      mutation.reset();
    }
    onOpenChange(next);
  };

  const barNoError = touched && !barNo.trim() ? "Bar number is required." : null;
  const jurisdictionError = touched && !jurisdiction.trim() ? "Jurisdiction is required." : null;

  const handleSubmit = () => {
    if (submitLockRef.current) return;
    setTouched(true);
    if (!barNo.trim() || !jurisdiction.trim()) return;
    submitLockRef.current = true;
    mutation.mutate(
      { barNo: barNo.trim(), jurisdiction: jurisdiction.trim() },
      {
        onSuccess: () => handleOpenChange(false),
        onError: () => {
          submitLockRef.current = false;
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="bg-bg-elevated rounded-lg max-w-[440px]">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">Become an Attorney</DialogTitle>
          <DialogDescription className="text-body-sm text-text-secondary">
            Enter your bar number and jurisdiction. A human reviewer approves attorney
            accounts — this isn&apos;t instant, so your account will show as pending until
            then.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div>
            <label htmlFor="bar-no" className="mb-1.5 block text-body-sm text-text-secondary">
              Bar number
            </label>
            <input
              id="bar-no"
              autoFocus
              value={barNo}
              onChange={(e) => setBarNo(e.target.value)}
              placeholder="e.g. NY1234567"
              className={`w-full rounded-sm border bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
                barNoError ? "border-danger" : "border-border-default"
              }`}
            />
            <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{barNoError}</p>
          </div>

          <div>
            <label
              htmlFor="jurisdiction"
              className="mb-1.5 block text-body-sm text-text-secondary"
            >
              Jurisdiction
            </label>
            <input
              id="jurisdiction"
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              placeholder="e.g. New York"
              className={`w-full rounded-sm border bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
                jurisdictionError ? "border-danger" : "border-border-default"
              }`}
            />
            <p className="mt-1 min-h-[1.25rem] text-caption text-danger">
              {jurisdictionError}
            </p>
          </div>

          {mutation.isError && (
            <p className="min-h-[1.25rem] text-caption text-danger">
              {mutation.error instanceof Error
                ? mutation.error.message
                : "Something went wrong. Please try again."}
            </p>
          )}
        </div>

        <DialogFooter className="bg-transparent border-t-0 p-0 mx-0 mb-0">
          <button
            type="button"
            onClick={() => handleOpenChange(false)}
            className="rounded-sm px-4 py-2.5 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="rounded-sm bg-accent px-4 py-2.5 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? "Submitting…" : "Submit"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
