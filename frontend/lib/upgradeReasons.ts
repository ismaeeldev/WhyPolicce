/**
 * Shared "why you're seeing this" copy for gated actions — used by both the
 * inline UpgradeModal (Step 5) and the full /upgrade page (Step 7) so the
 * two surfaces never drift out of sync for the same `reason` value.
 */
export const UPGRADE_REASON_COPY: Record<string, { title: string; body: string }> = {
  deep_search: {
    title: "This search needs Pro",
    body: "Deep search is a Pro feature — it runs a more thorough pass for the questions that deserve it.",
  },
  advanced_export: {
    title: "Advanced export needs Pro",
    body: "PDF, Markdown, and bulk exports are a Pro feature. Your basic JSON export stays free on every plan.",
  },
  default: {
    title: "Upgrade to WhyPolice Pro",
    body: "Get deep search, advanced export, and priority streaming.",
  },
};

export function getUpgradeReasonCopy(reason: string | null | undefined) {
  return UPGRADE_REASON_COPY[reason ?? "default"] ?? UPGRADE_REASON_COPY.default;
}
