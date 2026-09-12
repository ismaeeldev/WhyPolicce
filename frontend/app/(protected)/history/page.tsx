"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Download, History as HistoryIcon, Trash2, Upload } from "lucide-react";
import { useState } from "react";

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
import { Skeleton } from "@/components/ui/skeleton";
import { SessionCard } from "@/components/history/SessionCard";
import { apiFetch } from "@/lib/api-client";
import { useClearHistory, useSearchHistory } from "@/hooks/useSearchHistory";
import { useToastStore } from "@/stores/useToastStore";

import type { SessionDetail } from "@/hooks/useSessionDetail";

function downloadSessionJson(session: SessionDetail) {
  const blob = new Blob([JSON.stringify(session, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `whypolice-search-${session.id}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function HistoryPage() {
  const { data: sessions, isLoading, isError } = useSearchHistory();
  const clearHistory = useClearHistory();
  const showToast = useToastStore((s) => s.show);
  const [exportingId, setExportingId] = useState<string | null>(null);

  const handleExport = async (id: string) => {
    setExportingId(id);
    try {
      const detail = await apiFetch<SessionDetail>(`/api/search/${id}`);
      downloadSessionJson(detail);
      showToast("Session exported");
    } catch {
      showToast("Couldn't export that session — try again");
    } finally {
      setExportingId(null);
    }
  };

  const handleClear = async () => {
    try {
      await clearHistory.mutateAsync();
      showToast("History cleared");
    } catch {
      showToast("Couldn't clear history — try again");
    }
  };

  return (
    <div className="mx-auto w-full min-w-0 max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
      <div className="wp-page-toolbar mb-8 flex flex-col items-start justify-between gap-5 sm:flex-row sm:items-center">
        <h1 className="font-display text-h1 text-text-primary">History</h1>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled
            title="Import — coming soon"
            className="flex items-center gap-1.5 rounded-sm border border-border-default px-3 py-2 text-body-sm text-text-muted opacity-60 cursor-not-allowed"
          >
            <Upload className="h-3.5 w-3.5" />
            Import
          </button>
          <AlertDialog>
            <AlertDialogTrigger
              render={
                <button
                  type="button"
                  disabled={!sessions || sessions.length === 0}
                  className="flex items-center gap-1.5 rounded-sm border border-border-default px-3 py-2 text-body-sm text-danger hover:bg-danger-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                />
              }
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear history
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Clear all search history?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently deletes every saved search session. This can&apos;t be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleClear}
                  className="bg-danger text-danger-foreground hover:bg-danger/90"
                >
                  Clear history
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="mt-3 h-4 w-20" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-md border border-danger bg-danger-subtle p-6 text-center text-body-sm text-text-primary">
          Couldn&apos;t load your history right now — try refreshing.
        </div>
      ) : !sessions || sessions.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="flex flex-col gap-3">
          <AnimatePresence mode="popLayout">
            {sessions.map((session, i) => (
              <motion.div key={session.id} layout className="group relative">
                <SessionCard session={session} index={i} />
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    handleExport(session.id);
                  }}
                  disabled={exportingId === session.id}
                  aria-label="Export session as JSON"
                  className="absolute right-4 top-4 sm:right-6 sm:top-6 rounded-sm p-1.5 text-text-muted wp-touch-action opacity-0 transition-opacity duration-150 hover:bg-bg-subtle hover:text-text-primary group-hover:opacity-100 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-accent outline-none disabled:opacity-40"
                >
                  <Download className="h-4 w-4" />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border-strong bg-bg-elevated py-16 text-center"
    >
      <HistoryIcon className="h-8 w-8 text-text-muted" strokeWidth={1.5} />
      <p className="text-body text-text-primary">No searches yet</p>
      <p className="max-w-xs text-body-sm text-text-muted">
        Your search sessions will show up here once you ask WhyPolice something.
      </p>
    </motion.div>
  );
}
