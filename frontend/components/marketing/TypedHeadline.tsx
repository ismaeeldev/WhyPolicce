"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { SEARCH_CATEGORIES } from "@/components/search/SearchBar";

const QUESTIONS = SEARCH_CATEGORIES.flatMap((c) => c.examples);

const TYPE_SPEED_MS = 38;
const DELETE_SPEED_MS = 22;
const HOLD_MS = 2600;

/**
 * why.com's real rotating headline (verified via live DOM inspection, not
 * a screenshot guess) is a genuine character-by-character typewriter effect
 * with a blinking caret (`<span class="home-hero-question is-typing">` +
 * a `::after` `daily-cursor` animation) — not a cross-fade rotation like
 * our previous placeholder-only implementation. This rebuilds that same
 * pattern for WhyPolice's own public-safety questions.
 *
 * LCP safety (Revision 2/3's existing, measured finding: gating the H1
 * behind client JS cost ~550ms of real LCP): the FIRST question is
 * rendered as plain static text with `suppressHydrationWarning` before
 * the client typewriter takes over, so the real headline paints
 * immediately with the server HTML — animation only starts post-hydration
 * for the first delete/retype cycle onward, never blocking initial paint.
 */
export function TypedHeadline() {
  const [displayText, setDisplayText] = useState<string>(QUESTIONS[0]);
  // Same mount-detection pattern as components/layout/ThemeToggle.tsx —
  // useSyncExternalStore's server snapshot is always `false`, avoiding the
  // "setState synchronously in an effect" lint error a plain
  // `useState` + `useEffect(() => setMounted(true))` pair would trigger.
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const indexRef = useRef(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    let cancelled = false;

    const runCycle = (charIndex: number, phase: "deleting" | "typing") => {
      if (cancelled) return;
      const current = QUESTIONS[indexRef.current];

      if (phase === "deleting") {
        if (charIndex <= 0) {
          indexRef.current = (indexRef.current + 1) % QUESTIONS.length;
          timeoutRef.current = setTimeout(() => runCycle(0, "typing"), 300);
          return;
        }
        setDisplayText(current.slice(0, charIndex - 1));
        timeoutRef.current = setTimeout(() => runCycle(charIndex - 1, "deleting"), DELETE_SPEED_MS);
        return;
      }

      const nextQuestion = QUESTIONS[indexRef.current];
      if (charIndex >= nextQuestion.length) {
        setDisplayText(nextQuestion);
        timeoutRef.current = setTimeout(() => runCycle(nextQuestion.length, "deleting"), HOLD_MS);
        return;
      }
      setDisplayText(nextQuestion.slice(0, charIndex + 1));
      timeoutRef.current = setTimeout(() => runCycle(charIndex + 1, "typing"), TYPE_SPEED_MS);
    };

    timeoutRef.current = setTimeout(() => runCycle(QUESTIONS[0].length, "deleting"), HOLD_MS);

    return () => {
      cancelled = true;
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <h1 className="wp-hero-headline font-display text-text-primary">
      <span className="sr-only">Ask why. Understand what matters.</span>
      <span aria-hidden="true" className="wp-headline-stack">
        {QUESTIONS.map((question) => <span key={question} className="wp-headline-measure">{question}<span className="wp-typed-cursor" /></span>)}
        <span className="wp-headline-live"><span suppressHydrationWarning>{mounted ? displayText : QUESTIONS[0]}</span><span className="wp-typed-cursor" /></span>
      </span>
    </h1>
  );
}
