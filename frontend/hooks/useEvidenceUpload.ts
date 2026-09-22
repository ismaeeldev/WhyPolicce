"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/lib/api-client";

/**
 * Real evidence-upload flow — forum rebuild, Milestone 3 Step M3.1
 * (WhyPoliceForum_MasterGuide.md). Turns M2.3's disabled "coming soon"
 * placeholder into a real select → signed-URL → direct-to-GCS PUT →
 * register flow. The direct-to-GCS PUT deliberately does NOT go through
 * apiFetch (lib/api-client.ts) — that wrapper always sets
 * Content-Type: application/json and attaches our own backend's Bearer
 * token, neither of which belongs on a request going straight to Google's
 * signed URL, not our backend.
 */

export type FileType = "image" | "video" | "document";

function inferFileType(file: File): FileType {
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("video/")) return "video";
  return "document";
}

export function useEvidenceUpload(inquiryId: string) {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState<number | null>(null);

  const mutation = useMutation({
    mutationFn: async (file: File) => {
      setProgress(0);
      const fileType = inferFileType(file);

      const { uploadUrl, fileUrl } = await apiFetch<{ uploadUrl: string; fileUrl: string }>(
        "/api/v1/media/upload-url",
        {
          method: "POST",
          body: JSON.stringify({
            inquiry_id: inquiryId,
            file_type: fileType,
            size_bytes: file.size,
            content_type: file.type || "application/octet-stream",
          }),
        },
      );

      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", uploadUrl);
        xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            setProgress(Math.round((event.loaded / event.total) * 100));
          }
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) resolve();
          else reject(new Error(`Upload failed with status ${xhr.status}`));
        };
        xhr.onerror = () => reject(new Error("Upload failed"));
        xhr.send(file);
      });

      return apiFetch(`/api/v1/inquiries/${inquiryId}/attachments`, {
        method: "POST",
        body: JSON.stringify({ file_url: fileUrl, file_type: fileType, size_bytes: file.size }),
      });
    },
    onSuccess: () => {
      setProgress(null);
      // Real gap found during a full-scope re-audit, same stale-cache-key
      // class already fixed 3 times this session in other hooks
      // (useFollowInquiry, useRequestConsultation, useRespondToConsultation):
      // the feed card renders a paperclip icon driven by inquiry.hasAttachments
      // (InquiryCard.tsx), which lives in the ["inquiries", filters] cache —
      // only invalidating ["inquiry", inquiryId] left that stale for up to
      // staleTime (30s) after a real, successful upload/delete.
      queryClient.invalidateQueries({ queryKey: ["inquiry", inquiryId] });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    },
    onError: () => {
      setProgress(null);
    },
  });

  return { ...mutation, progress };
}

export function useDeleteAttachment(inquiryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (attachmentId: string) =>
      apiFetch(`/api/v1/inquiries/${inquiryId}/attachments/${attachmentId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inquiry", inquiryId] });
      queryClient.invalidateQueries({ queryKey: ["inquiries"] });
    },
  });
}
