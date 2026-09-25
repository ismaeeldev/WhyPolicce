"use client";

import { Pencil, Trash2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { ApiError } from "@/lib/api-client";
import { useDeleteComment } from "@/hooks/useInquiries";
import { useToastStore } from "@/stores/useToastStore";

/** Same pattern as InquiryEditDeleteControls, scoped to one comment. */
export function CommentEditDeleteControls({
  inquiryId,
  commentId,
  onEditClick,
}: {
  inquiryId: string;
  commentId: string;
  onEditClick: () => void;
}) {
  const deleteComment = useDeleteComment(inquiryId);
  const showToast = useToastStore((s) => s.show);

  return (
    // Real gap found during a UI audit: opacity-0 + hover/focus-reveal
    // has no touch equivalent — on mobile, a user must Tab in via
    // keyboard to ever see these controls, which means editing/deleting
    // your own comment was effectively undiscoverable on a phone.
    // Always visible below sm:, hover/focus-reveal only from sm: up.
    <div className="flex items-center gap-1 opacity-100 transition-opacity duration-150 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-within:opacity-100">
      <button
        type="button"
        onClick={onEditClick}
        aria-label="Edit comment"
        className="rounded-sm p-1 text-text-muted hover:bg-bg-subtle hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:opacity-100 outline-none"
      >
        <Pencil className="h-3 w-3" />
      </button>
      <AlertDialog>
        <AlertDialogTrigger
          render={
            <button
              type="button"
              aria-label="Delete comment"
              className="rounded-sm p-1 text-text-muted hover:bg-danger-subtle hover:text-danger transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:opacity-100 outline-none"
            />
          }
        >
          <Trash2 className="h-3 w-3" />
        </AlertDialogTrigger>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this comment?</AlertDialogTitle>
            <AlertDialogDescription>This can&apos;t be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                deleteComment.mutate(commentId, {
                  onError: (err) => {
                    showToast(err instanceof ApiError ? err.message : "Couldn't delete that comment. Try again.");
                  },
                })
              }
              className="bg-danger text-danger-foreground hover:bg-danger/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
