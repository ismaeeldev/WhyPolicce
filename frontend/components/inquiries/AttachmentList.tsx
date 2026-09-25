import { File, FileVideo, Image as ImageIcon } from "lucide-react";

import type { EvidenceAttachment } from "@/hooks/useInquiries";

const ICONS = { image: ImageIcon, video: FileVideo, document: File } as const;

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Read-only evidence list — forum rebuild, Milestone 3 Step M3.1
 * (WhyPoliceForum_MasterGuide.md). Shown to every non-author viewer;
 * the author sees the same list plus upload/remove controls via
 * EvidenceUploadField instead of this component.
 */
export function AttachmentList({ attachments }: { attachments: EvidenceAttachment[] }) {
  return (
    <div>
      <p className="mb-1.5 text-body-sm text-text-secondary">Evidence / media</p>
      <ul className="flex flex-col gap-1.5">
        {attachments.map((a) => {
          const Icon = ICONS[a.fileType];
          return (
            <li
              key={a.id}
              className="flex items-center gap-2.5 rounded-sm border border-border-default bg-bg-elevated px-3 py-2 transition-colors duration-150 hover:border-border-strong"
            >
              <Icon className="h-4 w-4 shrink-0 text-text-muted" strokeWidth={1.5} />
              <a
                href={a.fileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="min-w-0 flex-1 truncate text-body-sm text-accent hover:text-accent-hover transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                {a.originalFilename ?? a.fileUrl.split("/").pop()}
              </a>
              <span className="shrink-0 text-caption text-text-muted tabular-nums">
                {formatSize(a.sizeBytes)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
