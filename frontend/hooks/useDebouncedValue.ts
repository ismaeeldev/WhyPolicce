"use client";

import { useEffect, useState } from "react";

/**
 * Generic debounced-value hook — forum rebuild, Milestone 2 Step M2.2
 * (WhyPoliceForum_MasterGuide.md): the feed's search input must debounce
 * ~300ms before firing a request so every keystroke doesn't trigger one.
 * No debounce utility existed anywhere in this codebase before this.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
