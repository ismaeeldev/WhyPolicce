import { Upload } from "lucide-react";

/**
 * Evidence/media upload field — UI only, per M2.3's own explicit scope:
 * wired to a disabled placeholder until Milestone 3's real GCS upload-url
 * endpoint exists. Matches the old BillingPage's exact "coming soon"
 * pattern (disabled control + native title tooltip + opacity-60
 * cursor-not-allowed + caption-scale explainer beneath), not a new
 * pattern invented for this one field.
 */
export function EvidenceUploadField() {
  return (
    <div>
      <label className="mb-1.5 block text-body-sm text-text-secondary">
        Evidence / media
      </label>
      <button
        type="button"
        disabled
        title="File uploads coming soon"
        className="flex w-full items-center gap-3 rounded-sm border border-dashed border-border-default bg-bg-elevated px-4 py-4 text-left opacity-60 cursor-not-allowed"
      >
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-accent-subtle opacity-40 blur-md" />
          <div className="relative flex h-10 w-10 items-center justify-center rounded-full border border-border-default bg-bg-subtle">
            <Upload className="h-4 w-4 text-text-muted" strokeWidth={1.5} />
          </div>
        </div>
        <span className="text-body-sm text-text-muted">Attach photos or documents — coming soon</span>
      </button>
      <p className="mt-2 text-caption text-text-muted">
        File and photo uploads will be available here once evidence attachments are fully set up.
      </p>
    </div>
  );
}
