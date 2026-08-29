"use client";

import { useSyncExternalStore } from "react";

/**
 * Tracks browser connectivity — AgentGuide/03_MasterPromptGuide.md Step 8's
 * Bug Sweep calls out testing an offline network explicitly; this hook
 * (plus components/shared/OfflineBanner.tsx) is what actually surfaces that
 * state to the user, rather than leaving requests to fail silently/vaguely.
 *
 * useSyncExternalStore (not useState+useEffect) is the correct primitive
 * here — navigator.onLine is genuinely external browser state, and this
 * avoids the SSR/hydration mismatch a plain useState(navigator.onLine)
 * would hit (navigator doesn't exist server-side).
 */
function subscribe(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

function getSnapshot() {
  return navigator.onLine;
}

function getServerSnapshot() {
  return true; // assume online during SSR; corrected on the client immediately after hydration
}

export function useOnlineStatus(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
