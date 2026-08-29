"use client";

import { motion } from "framer-motion";
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
import { formatRelativeTime } from "@/lib/format";
import { TEMP_ID_PREFIX } from "@/hooks/useMemoryNotes";

import type { MemoryNote } from "@/hooks/useMemoryNotes";

const CARD_VARIANTS = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

/**
 * Memory note card — AgentGuide/01_ThemeGuideline.md §4.4, same hover-lift
 * language as SessionCard (Step 6) for visual consistency across the app's
 * card surfaces.
 */
export function NoteCard({
  note,
  index,
  onEdit,
  onDelete,
}: {
  note: MemoryNote;
  index: number;
  onEdit: () => void;
  onDelete: () => void;
}) {
  // A just-added note is optimistic until the POST resolves and swaps in
  // its real server id — editing/deleting it against a fake "temp-" id
  // would 404 on the backend, so disable those actions until it settles.
  const isSaving = note.id.startsWith(TEMP_ID_PREFIX);

  return (
    <motion.div
      layout
      variants={CARD_VARIANTS}
      initial="hidden"
      animate="visible"
      exit={{ opacity: 0, transition: { duration: 0.15 } }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.06, 0.36), ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -2 }}
      className="group rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6 shadow-none transition-shadow duration-150 hover:shadow-card"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-body text-text-primary leading-relaxed whitespace-pre-wrap">
          {note.content}
        </p>
        {isSaving ? (
          <span className="shrink-0 text-caption text-text-muted">Saving…</span>
        ) : (
        <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity duration-150 group-hover:opacity-100 focus-within:opacity-100">
          <button
            type="button"
            onClick={onEdit}
            aria-label="Edit note"
            className="rounded-sm p-1.5 text-text-muted hover:bg-bg-subtle hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent outline-none"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <AlertDialog>
            <AlertDialogTrigger
              render={
                <button
                  type="button"
                  aria-label="Delete note"
                  className="rounded-sm p-1.5 text-text-muted hover:bg-danger-subtle hover:text-danger transition-colors focus-visible:ring-2 focus-visible:ring-accent outline-none"
                />
              }
            >
              <Trash2 className="h-3.5 w-3.5" />
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this note?</AlertDialogTitle>
                <AlertDialogDescription>
                  WhyPolice will no longer keep this in mind for future searches.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={onDelete} className="bg-danger text-danger-foreground hover:bg-danger/90">
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
        )}
      </div>
      <p className="mt-2 text-caption text-text-muted">
        Updated {formatRelativeTime(note.updatedAt)}
      </p>
    </motion.div>
  );
}
