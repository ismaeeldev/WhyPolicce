import { create } from "zustand";

/**
 * Shared UI state for the upgrade/paywall modal — AgentGuide/01_ThemeGuideline.md §10.
 * ONE store per concern (Zustand rule) — this is the single owner of
 * "is the upgrade modal open, and why." No component should duplicate this
 * in local state.
 */
type UpgradeModalState = {
  isOpen: boolean;
  reason: string | null;
  open: (reason?: string) => void;
  close: () => void;
};

export const useUpgradeModalStore = create<UpgradeModalState>((set) => ({
  isOpen: false,
  reason: null,
  open: (reason) => set({ isOpen: true, reason: reason ?? null }),
  close: () => set({ isOpen: false, reason: null }),
}));
