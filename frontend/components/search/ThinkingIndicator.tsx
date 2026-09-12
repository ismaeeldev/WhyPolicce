"use client";

/**
 * Replaces the previous static single-ping dot (Revision 3 Step 7,
 * plan.md — client explicitly asked for a "moving like a real AI" loading
 * state, not a generic spinner). Three dots wave up and down with a
 * staggered phase offset via CSS animation-delay — reads as active,
 * continuous processing rather than a single one-shot ping that looks
 * "stuck" after its first cycle. Pure CSS (no Framer Motion instance
 * needed for a 3-node infinite loop), so this costs nothing extra during
 * the exact moment the app is already busy waiting on a network stream.
 */
export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2" role="status" aria-label="Thinking">
      <span className="flex items-end gap-1 h-4">
        <span className="wp-thinking-dot h-1.5 w-1.5 rounded-full bg-accent" style={{ animationDelay: "0ms" }} />
        <span className="wp-thinking-dot h-1.5 w-1.5 rounded-full bg-accent" style={{ animationDelay: "160ms" }} />
        <span className="wp-thinking-dot h-1.5 w-1.5 rounded-full bg-accent" style={{ animationDelay: "320ms" }} />
      </span>
      <p className="text-body-sm text-text-secondary">Thinking…</p>
    </div>
  );
}
