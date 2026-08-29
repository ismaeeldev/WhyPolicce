"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check } from "lucide-react";
import { useEffect } from "react";

import { useToastStore } from "@/stores/useToastStore";

const AUTO_DISMISS_MS = 2500;

/**
 * Toast / inline feedback — AgentGuide/01_ThemeGuideline.md §4.10.
 * Bottom-center on mobile, bottom-right on desktop; auto-dismisses, no
 * manual close needed for purely informational confirmations. Single
 * consumer of useToastStore, mounted once in providers.tsx.
 */
export function ToastViewport() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  return (
    <div className="fixed inset-x-0 bottom-4 z-[70] flex flex-col items-center gap-2 px-4 sm:inset-x-auto sm:right-4 sm:items-end pointer-events-none">
      <AnimatePresence initial={false}>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} id={toast.id} text={toast.text} onDismiss={dismiss} />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastItem({
  id,
  text,
  onDismiss,
}: {
  id: number;
  text: string;
  onDismiss: (id: number) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [id, onDismiss]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, transition: { duration: 0.15 } }}
      transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
      className="pointer-events-auto flex items-center gap-2 rounded-md border border-border-default bg-bg-elevated px-4 py-3 shadow-card"
    >
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/15">
        <Check className="h-3 w-3 text-success" />
      </span>
      <p className="text-body-sm text-text-primary">{text}</p>
    </motion.div>
  );
}
