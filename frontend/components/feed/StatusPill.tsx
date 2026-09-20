/**
 * Status pill — forum rebuild, Milestone 2 Step M2.2
 * (WhyPoliceForum_MasterGuide.md). Two states from the client's own spec:
 * "Awaiting Police Statement" (new --info/--info-subtle token pair,
 * proposed and confirmed — see globals.css's own comment for the real
 * contrast audit) and "Community Trace" (existing --warning/--warning-subtle,
 * matching the client's yellow-dot reference mockup).
 */
export type StatusTag = "community_trace" | "awaiting_police_statement";

const STATUS_CONFIG: Record<StatusTag, { label: string; bg: string; text: string; dot: string }> = {
  community_trace: {
    label: "Community Trace",
    bg: "bg-warning-subtle",
    text: "text-text-primary",
    dot: "bg-warning",
  },
  awaiting_police_statement: {
    label: "Awaiting Police Statement",
    bg: "bg-info-subtle",
    text: "text-text-primary",
    dot: "bg-info",
  },
};

export function StatusPill({ status }: { status: StatusTag }) {
  const config = STATUS_CONFIG[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-caption font-medium ${config.bg} ${config.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} aria-hidden="true" />
      {config.label}
    </span>
  );
}
