"use client";

import { AnimatePresence, motion } from "framer-motion";
import { BrainCircuit, Plus } from "lucide-react";
import { useState } from "react";

import { NoteCard } from "@/components/memory/NoteCard";
import { NoteFormDialog } from "@/components/memory/NoteFormDialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAddMemoryNote,
  useDeleteMemoryNote,
  useEditMemoryNote,
  useMemoryNotes,
} from "@/hooks/useMemoryNotes";
import { useToastStore } from "@/stores/useToastStore";

import type { MemoryNote } from "@/hooks/useMemoryNotes";

export default function MemoryPage() {
  const { data: notes, isLoading, isError } = useMemoryNotes();
  const addNote = useAddMemoryNote();
  const editNote = useEditMemoryNote();
  const deleteNote = useDeleteMemoryNote();
  const showToast = useToastStore((s) => s.show);

  const [formOpen, setFormOpen] = useState(false);
  const [editingNote, setEditingNote] = useState<MemoryNote | null>(null);

  const openAddForm = () => {
    setEditingNote(null);
    setFormOpen(true);
  };

  const openEditForm = (note: MemoryNote) => {
    setEditingNote(note);
    setFormOpen(true);
  };

  const handleSave = (content: string) => {
    if (editingNote) {
      editNote.mutate(
        { id: editingNote.id, content },
        { onSuccess: () => showToast("Note updated"), onError: () => showToast("Couldn't save that edit") },
      );
    } else {
      addNote.mutate(
        { content },
        { onSuccess: () => showToast("Note added"), onError: () => showToast("Couldn't add that note") },
      );
    }
    setFormOpen(false);
  };

  const handleDelete = (note: MemoryNote) => {
    deleteNote.mutate(
      { id: note.id },
      { onSuccess: () => showToast("Note deleted"), onError: () => showToast("Couldn't delete that note") },
    );
  };

  return (
    <div className="mx-auto w-full min-w-0 max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
      <div className="wp-page-toolbar mb-8 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-center">
        <div>
          <h1 className="font-display text-h1 text-text-primary">Memory</h1>
          <p className="mt-1 text-body-sm text-text-muted">
            Tell WhyPolice what to remember about you.
          </p>
        </div>
        <button
          type="button"
          onClick={openAddForm}
          className="flex shrink-0 items-center gap-1.5 rounded-sm bg-accent px-3.5 py-2 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          <Plus className="h-3.5 w-3.5" />
          Add note
        </button>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-2/3" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-md border border-danger bg-danger-subtle p-6 text-center text-body-sm text-text-primary">
          Couldn&apos;t load your memory notes right now — try refreshing.
        </div>
      ) : !notes || notes.length === 0 ? (
        <EmptyState onAdd={openAddForm} />
      ) : (
        <div className="flex flex-col gap-3">
          <AnimatePresence mode="popLayout">
            {notes.map((note, i) => (
              <NoteCard
                key={note.id}
                note={note}
                index={i}
                onEdit={() => openEditForm(note)}
                onDelete={() => handleDelete(note)}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      <NoteFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        initialContent={editingNote?.content ?? ""}
        onSave={handleSave}
        saving={addNote.isPending || editNote.isPending}
      />
    </div>
  );
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border-strong bg-bg-elevated py-16 text-center px-6"
    >
      <BrainCircuit className="h-8 w-8 text-text-muted" strokeWidth={1.5} />
      <p className="text-body text-text-primary">Tell WhyPolice what to remember about you</p>
      <p className="max-w-sm text-body-sm text-text-muted">
        Add a short fact or preference — like your profession, location, or how you like answers
        phrased — and future searches can take it into account.
      </p>
      <button
        type="button"
        onClick={onAdd}
        className="mt-2 flex items-center gap-1.5 rounded-sm bg-accent px-4 py-2 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        <Plus className="h-3.5 w-3.5" />
        Add your first note
      </button>
    </motion.div>
  );
}
