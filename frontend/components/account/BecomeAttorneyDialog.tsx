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
import { US_STATES } from "@/lib/us-states";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { useToastStore } from "@/stores/useToastStore";

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
  const [legalFirstName, setLegalFirstName] = useState("");
  const [legalLastName, setLegalLastName] = useState("");
  const [barNo, setBarNo] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [firmEmail, setFirmEmail] = useState("");
  // Scope Revision 1 §5.5 — optional, client's own wording: "if provided".
  const [firmWebsite, setFirmWebsite] = useState("");
  const [touched, setTouched] = useState(false);
  const mutation = useBecomeAttorney();
  const showToast = useToastStore((s) => s.show);
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
      setLegalFirstName("");
      setLegalLastName("");
      setBarNo("");
      setJurisdiction("");
      setFirmEmail("");
      setFirmWebsite("");
      setTouched(false);
      submitLockRef.current = false;
      mutation.reset();
    }
    onOpenChange(next);
  };

  const legalFirstNameError = touched && !legalFirstName.trim() ? "Legal first name is required." : null;
  const legalLastNameError = touched && !legalLastName.trim() ? "Legal last name is required." : null;
  const barNoError = touched && !barNo.trim() ? "Bar number is required." : null;
  const jurisdictionError = touched && !jurisdiction.trim() ? "Jurisdiction is required." : null;
  const firmEmailError = touched && !firmEmail.trim() ? "Firm email is required." : null;

  const handleSubmit = () => {
    if (submitLockRef.current) return;
    setTouched(true);
    if (
      !legalFirstName.trim() ||
      !legalLastName.trim() ||
      !barNo.trim() ||
      !jurisdiction.trim() ||
      !firmEmail.trim()
    ) {
      return;
    }
    submitLockRef.current = true;
    mutation.mutate(
      {
        barNo: barNo.trim(),
        jurisdiction: jurisdiction.trim(),
        legalFirstName: legalFirstName.trim(),
        legalLastName: legalLastName.trim(),
        firmEmail: firmEmail.trim(),
        firmWebsite: firmWebsite.trim() || undefined,
      },
      {
        onSuccess: (result) => {
          handleOpenChange(false);
          // §5.5 — non-blocking: the application still submits normally,
          // this is just a heads-up in case it's a real typo.
          if (result.domainMismatchWarning) {
            showToast(result.domainMismatchWarning);
          }
        },
        onError: () => {
          submitLockRef.current = false;
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {/* Real bug found via the E2E audit suite (not caught by review): with
          5 fields (up from the original 2), this dialog's content genuinely
          exceeds shared ui/dialog.tsx's 85vh cap on common viewport heights
          (measured: 750px content vs. a 612px cap on a 720px-tall window).
          That shared primitive puts overflow-y-auto on an INNER div with no
          height of its own while the OUTER Popup is overflow-y:visible — so
          nothing ever actually clips/scrolls, and Submit renders unreachably
          below the fold. Fixing only here (not in the shared primitive,
          which other, shorter dialogs still rely on as-is) by capping this
          dialog's own content to a real, scrollable height. */}
      <DialogContent className="bg-bg-elevated rounded-lg max-w-[440px]">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">Become an Attorney</DialogTitle>
          <DialogDescription className="text-body-sm text-text-secondary">
            Enter your legal name, bar registration, and firm email. A human reviewer
            approves attorney accounts — this isn&apos;t instant, so your account will
            show as pending until then.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 max-h-[50vh] overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="legal-first-name" className="mb-1.5 block text-body-sm text-text-secondary">
                Legal first name
              </label>
              <input
                id="legal-first-name"
                autoFocus
                value={legalFirstName}
                onChange={(e) => setLegalFirstName(e.target.value)}
                placeholder="Jane"
                className={`w-full rounded-sm border bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
                  legalFirstNameError ? "border-danger" : "border-border-default"
                }`}
              />
              <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{legalFirstNameError}</p>
            </div>
            <div>
              <label htmlFor="legal-last-name" className="mb-1.5 block text-body-sm text-text-secondary">
                Legal last name
              </label>
              <input
                id="legal-last-name"
                value={legalLastName}
                onChange={(e) => setLegalLastName(e.target.value)}
                placeholder="Doe"
                className={`w-full rounded-sm border bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
                  legalLastNameError ? "border-danger" : "border-border-default"
                }`}
              />
              <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{legalLastNameError}</p>
            </div>
          </div>

          <div>
            <label htmlFor="bar-no" className="mb-1.5 block text-body-sm text-text-secondary">
              Bar number
            </label>
            <input
              id="bar-no"
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
            <Select
              value={jurisdiction}
              onValueChange={(value) => setJurisdiction(value as string)}
            >
              <SelectTrigger
                id="jurisdiction"
                className={jurisdictionError ? "border-danger" : undefined}
              >
                <SelectValue placeholder="Select a state">
                  {(value: string) => US_STATES.find((s) => s.code === value)?.name ?? value}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {US_STATES.map((s) => (
                  <SelectItem key={s.code} value={s.code}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="mt-1 min-h-[1.25rem] text-caption text-danger">
              {jurisdictionError}
            </p>
          </div>

          <div>
            <label htmlFor="firm-email" className="mb-1.5 block text-body-sm text-text-secondary">
              Firm email
            </label>
            <input
              id="firm-email"
              type="email"
              value={firmEmail}
              onChange={(e) => setFirmEmail(e.target.value)}
              placeholder="jane@yourfirm.com"
              className={`w-full rounded-sm border bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
                firmEmailError ? "border-danger" : "border-border-default"
              }`}
            />
            <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{firmEmailError}</p>
          </div>

          <div>
            <label htmlFor="firm-website" className="mb-1.5 block text-body-sm text-text-secondary">
              Firm website <span className="text-text-muted">(optional)</span>
            </label>
            <input
              id="firm-website"
              value={firmWebsite}
              onChange={(e) => setFirmWebsite(e.target.value)}
              placeholder="yourfirm.com"
              className="w-full rounded-sm border border-border-default bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
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
