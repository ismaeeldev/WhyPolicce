"use client";

import { useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const MAX_LENGTH = 2000;

/**
 * Add/Edit memory note form — AgentGuide/01_ThemeGuideline.md §4.8 (single
 * textarea, save/cancel). One dialog handles both add (initialContent="")
 * and edit (initialContent=note.content) to avoid duplicating the form.
 */
export function NoteFormDialog({
  open,
  onOpenChange,
  initialContent = "",
  onSave,
  saving,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialContent?: string;
  onSave: (content: string) => void;
  saving: boolean;
}) {
  const [content, setContent] = useState(initialContent);

  // React's "adjust state during render" pattern (not an effect) — resets
  // the textarea whenever the dialog opens, or (defensively) if the target
  // note changes while already open, same technique AnswerPanel uses for
  // its scroll-lock reset (Step 5).
  const [prevKey, setPrevKey] = useState(`${open}|${initialContent}`);
  const key = `${open}|${initialContent}`;
  if (key !== prevKey) {
    setPrevKey(key);
    if (open) setContent(initialContent);
  }

  const trimmed = content.trim();
  const isEdit = initialContent.length > 0;

  const handleSave = () => {
    if (!trimmed) return;
    onSave(trimmed);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-bg-elevated rounded-lg max-w-[440px]">
        <DialogHeader>
          <DialogTitle className="font-display text-xl">
            {isEdit ? "Edit memory note" : "Add memory note"}
          </DialogTitle>
          <DialogDescription className="text-body-sm text-text-secondary">
            A short fact or preference WhyPolice can keep in mind for future searches.
          </DialogDescription>
        </DialogHeader>

        <textarea
          autoFocus
          value={content}
          onChange={(e) => setContent(e.target.value.slice(0, MAX_LENGTH))}
          placeholder="e.g. I'm a freelance graphic designer based in Toronto"
          rows={4}
          className="w-full rounded-sm border border-border-default bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none resize-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-colors"
        />
        <p className="text-caption text-text-muted text-right -mt-2">
          {content.length}/{MAX_LENGTH}
        </p>

        <DialogFooter className="bg-transparent border-t-0 p-0 mx-0 mb-0">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded-sm px-4 py-2.5 text-body-sm text-text-secondary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!trimmed || saving}
            className="rounded-sm bg-accent px-4 py-2.5 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
