/**
 * Analytics scaffold — AgentGuide/02_ApplicationFlow.md §5.2.
 * No-op/console.debug implementation for MVP. Every meaningful action in the
 * app calls this one function at the right call sites, so wiring a real
 * provider (PostHog, GA, etc.) later is a one-line change here, not a
 * codebase-wide refactor.
 */
export function trackEvent(name: string, props?: Record<string, unknown>): void {
  if (process.env.NODE_ENV !== "production") {
    console.debug(`[analytics] ${name}`, props ?? {});
  }
}
