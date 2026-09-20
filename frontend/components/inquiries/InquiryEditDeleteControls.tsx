"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";

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
import { useDeleteInquiry } from "@/hooks/useInquiries";
import { useToastStore } from "@/stores/useToastStore";

/**
 * Edit/Delete controls on the inquiry itself — visible ONLY to the
 * inquiry's own author (M2.4). Reuses the History screen's exact
 * export-button hover-reveal pattern (opacity-0 group-hover:opacity-100
 * + focus-visible:opacity-100 for keyboard users) and the existing
 * "Clear history" AlertDialog's destructive-action treatment — never
 * a new confirmation pattern invented for this one action.
 *
 * This is a UI-only convenience check (only the owner sees these
 * buttons at all) — the real security boundary is M1.4's own
 * server-side ownership enforcement, already tested independently.
 */
export function InquiryEditDeleteControls({
  inquiryId,
  onEditClick,
}: {
  inquiryId: string;
  onEditClick: () => void;
}) {
  const router = useRouter();
  const deleteInquiry = useDeleteInquiry(inquiryId);
  const showToast = useToastStore((s) => s.show);

  const handleDelete = async () => {
    await deleteInquiry.mutateAsync();
    showToast("Inquiry deleted");
    router.push("/");
  };

  return (
    <div className="absolute right-0 top-0 flex items-center gap-1 opacity-0 transition-opacity duration-150 group-hover:opacity-100 focus-within:opacity-100">
      <button
        type="button"
        onClick={onEditClick}
        aria-label="Edit inquiry"
        className="rounded-sm p-1.5 text-text-muted hover:bg-bg-subtle hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:opacity-100 outline-none"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
      <AlertDialog>
        <AlertDialogTrigger
          render={
            <button
              type="button"
              aria-label="Delete inquiry"
              className="rounded-sm p-1.5 text-text-muted hover:bg-danger-subtle hover:text-danger transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:opacity-100 outline-none"
            />
          }
        >
          <Trash2 className="h-3.5 w-3.5" />
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this inquiry?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the inquiry and its full comment thread. This can&apos;t be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-danger text-danger-foreground hover:bg-danger/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
