"use client";

import { File, FileVideo, Image as ImageIcon, Upload, X } from "lucide-react";
import { useRef, useState } from "react";

import { UpgradeModal } from "@/components/inquiries/UpgradeModal";
import { ApiError } from "@/lib/api-client";
import { useDeleteAttachment, useEvidenceUpload } from "@/hooks/useEvidenceUpload";
import type { EvidenceAttachment } from "@/hooks/useInquiries";

const ICONS = { image: ImageIcon, video: FileVideo, document: File } as const;

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Real evidence/media upload field — forum rebuild, Milestone 3 Step
 * M3.1 (WhyPoliceForum_MasterGuide.md). Replaces M2.3's disabled
 * "coming soon" placeholder. Lives on the author's own thread page
 * (Manual Step decision, user-confirmed): the real upload flow needs a
 * genuine, already-created inquiry_id, which doesn't exist yet on the
 * new-inquiry create form.
 */
export function EvidenceUploadField({
  inquiryId,
  attachments,
}: {
  inquiryId: string;
  attachments: EvidenceAttachment[];
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);
  const upload = useEvidenceUpload(inquiryId);
  const deleteAttachment = useDeleteAttachment(inquiryId);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    setError(null);
    upload.mutate(file, {
      onError: (err) => {
        if (err instanceof ApiError && err.code === "upgrade_required") {
          setUpgradeModalOpen(true);
        } else if (err instanceof ApiError && err.code === "not_implemented") {
          setError("File uploads aren't fully set up yet — check back soon.");
        } else {
          setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
        }
      },
    });
  };

  return (
    <div>
      <label className="mb-1.5 block text-body-sm text-text-secondary">Evidence / media</label>

      {attachments.length > 0 && (
        <ul className="mb-2 flex flex-col gap-1.5">
          {attachments.map((a) => {
            const Icon = ICONS[a.fileType];
            return (
              <li
                key={a.id}
                className="flex items-center gap-2.5 rounded-sm border border-border-default bg-bg-elevated px-3 py-2"
              >
                <Icon className="h-4 w-4 shrink-0 text-text-muted" strokeWidth={1.5} />
                <span className="min-w-0 flex-1 truncate text-body-sm text-text-primary">
                  {a.fileUrl.split("/").pop()}
                </span>
                <span className="shrink-0 text-caption text-text-muted tabular-nums">
                  {formatSize(a.sizeBytes)}
                </span>
                <button
                  type="button"
                  aria-label="Remove attachment"
                  onClick={() => deleteAttachment.mutate(a.id)}
                  disabled={deleteAttachment.isPending}
                  className="shrink-0 rounded-sm p-1 text-text-muted transition-colors hover:text-danger disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,video/*,application/pdf"
        className="hidden"
        onChange={handleFileSelect}
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={upload.isPending}
        className="flex w-full items-center gap-3 rounded-sm border border-dashed border-border-default bg-bg-elevated px-4 py-4 text-left transition-colors hover:border-accent disabled:cursor-not-allowed disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center">
          <div className="absolute inset-0 rounded-full bg-accent-subtle opacity-40 blur-md" />
          <div className="relative flex h-10 w-10 items-center justify-center rounded-full border border-border-default bg-bg-subtle">
            <Upload className="h-4 w-4 text-text-muted" strokeWidth={1.5} />
          </div>
        </div>
        <span className="text-body-sm text-text-muted">
          {upload.isPending
            ? upload.progress !== null
              ? `Uploading… ${upload.progress}%`
              : "Uploading…"
            : "Attach a photo, video, or document"}
        </span>
      </button>

      {upload.isPending && upload.progress !== null && (
        <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-bg-subtle">
          <div
            className="h-full rounded-full bg-accent transition-all duration-150"
            style={{ width: `${upload.progress}%` }}
          />
        </div>
      )}

      {error && <p className="mt-2 text-caption text-danger">{error}</p>}

      <UpgradeModal
        open={upgradeModalOpen}
        onOpenChange={setUpgradeModalOpen}
        title="This inquiry needs the $2.99 upgrade"
        description="Free inquiries can attach 1 file up to 5MB. Upgrade to attach up to 5 files and 50MB total."
      />
    </div>
  );
}
