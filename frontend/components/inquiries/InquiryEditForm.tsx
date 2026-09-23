"use client";

import { useRef, useState } from "react";

import { StatusTagSelector } from "@/components/inquiries/StatusTagSelector";
import { UpgradeModal } from "@/components/inquiries/UpgradeModal";
import type { StatusTag } from "@/components/feed/StatusPill";
import { ApiError } from "@/lib/api-client";
import { US_STATES } from "@/lib/us-states";
import { useInquiryUpgradeCheckout } from "@/hooks/useForumBilling";
import { useUpdateInquiry, type Inquiry } from "@/hooks/useInquiries";

const FREE_TIER_CHAR_LIMIT = 250;

/**
 * Inquiry edit form — forum rebuild, Milestone 2 Step M2.4
 * (WhyPoliceForum_MasterGuide.md). Reuses M2.3's form fields/pattern
 * where practical (state dropdown, StatusTagSelector) rather than
 * duplicating a second form implementation, per this step's own
 * explicit requirement. Pre-filled with the inquiry's current content.
 *
 * Real Bug Fix scenario handled by construction, not extra code: this
 * form only ever calls the update mutation on an explicit Save click —
 * closing the tab or navigating away mid-edit never calls the API at
 * all, so the original content on the server is always intact; there
 * is no auto-save/draft-persistence path that could partially apply an
 * unsaved edit.
 *
 * Real gap found and fixed: the backend correctly enforces the
 * free-tier 250-char limit on edits too (not just creation), but this
 * form gave zero warning before Save — a citizen editing a free post
 * past the limit only found out via a raw error message after
 * clicking Save, with no character counter and no path to actually
 * upgrade from here. Mirrors the create form's own counter/upgrade-
 * modal pattern, but conditional on inquiry.tier — an already-
 * `expanded` (paid) inquiry has no length limit at all when editing,
 * so the counter/modal only ever applies to a genuinely free-tier one.
 */
export function InquiryEditForm({
  inquiry,
  onCancel,
  onSaved,
}: {
  inquiry: Inquiry;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(inquiry.title);
  const [description, setDescription] = useState(inquiry.description);
  const [state, setState] = useState(inquiry.state);
  const [city, setCity] = useState(inquiry.city);
  const [precinct, setPrecinct] = useState(inquiry.precinct ?? "");
  const [statusTag, setStatusTag] = useState<StatusTag>(inquiry.statusTag);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);

  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const updateInquiry = useUpdateInquiry(inquiry.id);
  const inquiryUpgradeCheckout = useInquiryUpgradeCheckout();

  const isFreeTier = inquiry.tier === "free";
  const charCount = description.length;
  const overLimit = isFreeTier && charCount > FREE_TIER_CHAR_LIMIT;

  const handleSave = () => {
    if (overLimit) {
      setUpgradeModalOpen(true);
      return;
    }
    setSaveError(null);
    updateInquiry.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        state,
        city: city.trim(),
        precinct: precinct.trim(),
        statusTag,
      },
      {
        onSuccess: onSaved,
        onError: (err) => {
          setSaveError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
        },
      },
    );
  };

  const handleTrimInstead = () => {
    descriptionRef.current?.focus();
  };

  return (
    <div className="flex flex-col gap-4 rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6">
      <div>
        <label className="mb-1.5 block text-body-sm text-text-secondary">Title</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="h-11 w-full rounded-sm border border-border-default bg-bg px-3.5 text-body text-text-primary outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-body-sm text-text-secondary">Description</label>
        <textarea
          ref={descriptionRef}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={6}
          className="w-full rounded-sm border border-border-default bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none resize-none focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
        {isFreeTier && (
          <div className="mt-1 flex items-center justify-end">
            <p className={`text-caption tabular-nums ${overLimit ? "text-warning" : "text-text-muted"}`}>
              {charCount}/{FREE_TIER_CHAR_LIMIT}
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1.5 block text-body-sm text-text-secondary">State</label>
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="h-11 w-full rounded-sm border border-border-default bg-bg px-3 text-body text-text-primary outline-none focus:border-accent"
          >
            {US_STATES.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-body-sm text-text-secondary">City</label>
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="h-11 w-full rounded-sm border border-border-default bg-bg px-3.5 text-body text-text-primary outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
          />
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-body-sm text-text-secondary">
          Precinct <span className="text-text-muted">(optional)</span>
        </label>
        <input
          value={precinct}
          onChange={(e) => setPrecinct(e.target.value)}
          className="h-11 w-full rounded-sm border border-border-default bg-bg px-3.5 text-body text-text-primary outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
      </div>

      <StatusTagSelector value={statusTag} onChange={setStatusTag} />

      {saveError && (
        <div className="rounded-md border border-danger bg-danger-subtle p-3">
          <p className="text-body-sm text-text-primary">{saveError}</p>
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={updateInquiry.isPending || !title.trim() || !description.trim() || !city.trim()}
          className="rounded-sm bg-accent px-4 py-2 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          {updateInquiry.isPending ? "Saving…" : "Save changes"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-sm px-4 py-2 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Cancel
        </button>
      </div>

      {isFreeTier && (
        <UpgradeModal
          open={upgradeModalOpen}
          onOpenChange={setUpgradeModalOpen}
          onTrimInstead={handleTrimInstead}
          descriptionTextareaRef={descriptionRef}
          primaryAction={{
            label: "Upgrade for $2.99",
            onClick: () => inquiryUpgradeCheckout.mutate(inquiry.id),
            isPending: inquiryUpgradeCheckout.isPending,
          }}
        />
      )}
    </div>
  );
}
