import { Clock, ShieldCheck, ShieldX } from "lucide-react";

/**
 * Pending/approved/rejected attorney-verification banner — M2.1's own UI
 * Details: --warning-subtle background with --text-primary copy (NOT
 * --warning text — ThemeGuideline §1.4's contrast audit found warning-
 * family text fails AA on that background; --warning is icon/border-only
 * here, matching the Pro-badge fix pattern in §4.6).
 */
export function AttorneyStatusBanner({
  status,
}: {
  status: "pending" | "approved" | "rejected";
}) {
  if (status === "pending") {
    return (
      <div className="flex items-start gap-3 rounded-md border border-warning bg-warning-subtle p-4">
        <Clock className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
        <div>
          <p className="text-body-sm font-medium text-text-primary">
            Your attorney application is pending review
          </p>
          <p className="mt-0.5 text-body-sm text-text-primary">
            A human reviewer checks bar number and jurisdiction — this isn&apos;t automatic, so
            it may take a few days. You&apos;ll keep your citizen access in the meantime.
          </p>
        </div>
      </div>
    );
  }

  if (status === "rejected") {
    return (
      <div className="flex items-start gap-3 rounded-md border border-danger bg-danger-subtle p-4">
        <ShieldX className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
        <p className="text-body-sm text-text-primary">
          Your attorney application was not approved. Contact support if you believe this was
          a mistake.
        </p>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 rounded-md border border-accent bg-accent-subtle p-4">
      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-accent-bright" />
      <p className="text-body-sm text-text-primary">
        Your attorney account is verified.
      </p>
    </div>
  );
}
