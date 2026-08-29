"use client";

import { useEffect, useLayoutEffect, useRef } from "react";

/**
 * GSAP ScrollTrigger-driven staggered reveal for marketing sections —
 * AgentGuide/01_ThemeGuideline.md §7.1 (GSAP reserved for scroll-driven
 * storytelling) and §7.2 (stagger 60-100ms, trigger ~20% viewport entry,
 * opacity + translateY(16px->0)). §7.4 point 3: fires once, never re-triggers.
 *
 * GSAP is dynamically imported (not a static top-level import) — Lighthouse
 * traced it to ~580ms of blocking script evaluation on initial load for a
 * library that's only needed once the user actually scrolls below the fold.
 * The initial hidden state is set synchronously via plain inline styles
 * (useLayoutEffect, no GSAP needed) so there's no flash-of-visible-content
 * while the GSAP chunk loads in the background.
 */
export function ScrollReveal({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  // Runs before paint, plain DOM — avoids a visible flash before GSAP loads.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;
    for (const child of Array.from(el.children)) {
      const style = (child as HTMLElement).style;
      style.opacity = "0";
      style.transform = "translateY(16px)";
    }
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;

    let trigger: { kill: () => void } | undefined;
    let cancelled = false;

    import("gsap").then(({ gsap }) =>
      import("gsap/ScrollTrigger").then(({ ScrollTrigger }) => {
        if (cancelled || !ref.current) return;
        gsap.registerPlugin(ScrollTrigger);
        const targets = Array.from(ref.current.children);
        trigger = ScrollTrigger.create({
          trigger: ref.current,
          start: "top 80%",
          once: true,
          onEnter: () => {
            gsap.to(targets, {
              opacity: 1,
              y: 0,
              duration: 0.5,
              ease: "power3.out",
              stagger: 0.08,
            });
          },
        });
      }),
    );

    return () => {
      cancelled = true;
      trigger?.kill();
    };
  }, []);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
