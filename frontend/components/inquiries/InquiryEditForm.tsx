"use client";

import { useState } from "react";

import { StatusTagSelector } from "@/components/inquiries/StatusTagSelector";
import type { StatusTag } from "@/components/feed/StatusPill";
import { US_STATES } from "@/lib/us-states";
import { useUpdateInquiry, type Inquiry } from "@/hooks/useInquiries";

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

  const updateInquiry = useUpdateInquiry(inquiry.id);

  const handleSave = () => {
    updateInquiry.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        state,
        city: city.trim(),
        precinct: precinct.trim(),
        statusTag,
      },
      { onSuccess: onSaved },
    );
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
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={6}
          className="w-full rounded-sm border border-border-default bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none resize-none focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
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
    </div>
  );
}
