"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

/**
 * Top-of-viewport route progress indicator — AgentGuide/01_ThemeGuideline.md §9.
 * Fires on every pathname/search-param change, completes shortly after the
 * new route paints. z-50 per the z-index scale in §3.2 — above the sticky nav.
 */
function ProgressBarInner() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    setVisible(true);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setVisible(false), 350);
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [pathname, searchParams]);

  return (
    <div
      aria-hidden="true"
      className={`fixed top-0 left-0 z-50 h-[3px] bg-accent transition-all duration-300 ease-out motion-reduce:transition-none ${
        visible ? "w-full opacity-100" : "w-0 opacity-0"
      }`}
    />
  );
}

export function RouteProgressBar() {
  return (
    <Suspense fallback={null}>
      <ProgressBarInner />
    </Suspense>
  );
}
