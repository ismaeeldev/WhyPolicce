import { create } from "zustand";

/**
 * Shared UI state for the toast/inline-feedback system —
 * AgentGuide/01_ThemeGuideline.md §4.10. ONE store per concern (Zustand
 * rule) — any component can call useToastStore.getState().show(text)
 * without owning toast state itself. Never stacks more than 2 at once, per
 * §4.10 — a third push replaces the oldest.
 */
type Toast = { id: number; text: string };

type ToastState = {
  toasts: Toast[];
  show: (text: string) => void;
  dismiss: (id: number) => void;
};

let nextId = 1;

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  show: (text) =>
    set((state) => ({
      toasts: [...state.toasts, { id: nextId++, text }].slice(-2),
    })),
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
