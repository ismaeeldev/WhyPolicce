import { Clock, ShieldCheck, ShieldX } from "lucide-react";
import Link from "next/link";

/**
 * Pending/approved/rejected attorney-verification banner — M2.1's own UI
 * Details: --warning-subtle background with --text-primary copy (NOT
 * --warning text — ThemeGuideline §1.4's contrast audit found warning-
 * family text fails AA on that background; --warning is icon/border-only
 * here, matching the Pro-badge fix pattern in §4.6).
 */
export function AttorneyStatusBanner({
  status,
  onReapplyClick,
}: {
  status: "pending" | "approved" | "rejected";
  // Real gap found during a full-scope re-audit: a rejected attorney
  // had no path back at all — the backend only ever blocked a
  // reapplication, matching this dead-end UI. Now that resubmitting
  // moves the account back to pending for a real admin to re-review,
  // this banner needs a real way to trigger that, not just a
  // "contact support" dead end for what could just be a correction
  // (a typo'd bar number, a jurisdiction mismatch) rather than a
  // genuine dispute.
  onReapplyClick?: () => void;
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
        <div className="min-w-0 flex-1">
          <p className="text-body-sm text-text-primary">
            Your attorney application was not approved.{" "}
            <a
              href="mailto:support@whypolice.com"
              className="font-medium underline underline-offset-2 hover:text-danger"
            >
              Contact support
            </a>{" "}
            if you believe this was a mistake.
          </p>
          {onReapplyClick && (
            <button
              type="button"
              onClick={onReapplyClick}
              className="mt-2 text-body-sm font-medium text-danger underline underline-offset-2 hover:text-danger/80 transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
            >
              Submit a new application →
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 rounded-md border border-accent bg-accent-subtle p-4">
      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-accent-bright" />
      <div className="min-w-0 flex-1">
        <p className="text-body-sm text-text-primary">
          Your attorney account is verified.
        </p>
        {/* Real gap found: this banner confirmed verification with no
            next step at all — an approved attorney had no obvious way
            to reach their own portal from here, only the generic "For
            Attorneys" nav link that reads as public marketing copy. */}
        <Link
          href="/attorneys/dashboard"
          className="mt-2 inline-block text-body-sm font-medium text-accent-bright underline underline-offset-2 hover:text-accent-hover transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Go to your attorney dashboard →
        </Link>
      </div>
    </div>
  );
}
