"use client";

import { MessageSquare, Paperclip } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { StatusPill } from "@/components/feed/StatusPill";
import { ApiError } from "@/lib/api-client";
import { useFollowInquiry, useUnfollowInquiry } from "@/hooks/useFollowInquiry";
import type { Inquiry } from "@/hooks/useInquiries";
import { useToastStore } from "@/stores/useToastStore";

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

/**
 * Home feed inquiry card — forum rebuild, Milestone 2 Step M2.2
 * (WhyPoliceForum_MasterGuide.md). Card shell reuses ThemeGuideline §4.4's
 * existing spec exactly (--bg-elevated, --radius-md, --border hairline,
 * p-6/p-4). Follower/comment counts use tabular-nums in a reserved-width
 * container so a 1->2 digit change never shifts adjacent content
 * (Standing UI Discipline rule 12).
 *
 * `extraAction` (added M2.4): an optional slot rendered alongside
 * Follow, reused by the attorney portal's "Request Consultation"
 * button rather than duplicating this whole card for that one
 * additional action — the citizen feed simply never passes it.
 */
export function InquiryCard({
  inquiry,
  extraAction,
  isLatest,
}: {
  inquiry: Inquiry;
  extraAction?: React.ReactNode;
  /** Scope Revision 3 follow-up — a real visual-monotony gap found during
   * a fresh audit at realistic scale (80+ cards): every card shared the
   * exact same shape/border/accent treatment with no rhythm break, which
   * read as repetitive rather than "sharp, minimalist, authoritative."
   * Only the caller (HomeFeedClient) knows whether this card is genuinely
   * the most recent unfiltered record — never guessed here from card
   * position alone, since that would be wrong on page 2 or under an
   * active filter/search. */
  isLatest?: boolean;
}) {
  const [pressed, setPressed] = useState(false);
  const followMutation = useFollowInquiry();
  const unfollowMutation = useUnfollowInquiry();
  const showToast = useToastStore((s) => s.show);

  // Real bug reported by the user: a logged-out visitor clicking Follow
  // saw the button optimistically flip, then silently snap back (the
  // hook's onError rollback firing on the backend's real 401) with
  // absolutely no explanation why — it just "fluctuated." The button was
  // never gated on auth state to begin with (same as the thread page's
  // own Follow button), so this distinguishes "you're not signed in"
  // from any other genuine failure and says so.
  const onFollowError = (err: unknown) => {
    showToast(
      err instanceof ApiError && err.status === 401
        ? "Sign in to follow an inquiry."
        : err instanceof ApiError
          ? err.message
          : "Couldn't update follow status. Try again.",
    );
  };

  const handleFollowClick = () => {
    if (inquiry.isFollowing) {
      unfollowMutation.mutate(inquiry.id, { onError: onFollowError });
    } else {
      followMutation.mutate(inquiry.id, { onError: onFollowError });
    }
  };

  const dateLabel = dateFormatter.format(new Date(inquiry.createdAt));
  const locationLabel = [inquiry.city, inquiry.state].filter(Boolean).join(", ");
  const metaParts = [locationLabel];
  if (inquiry.precinct) metaParts.push(inquiry.precinct);

  const accentClass =
    inquiry.statusTag === "awaiting_police_statement" ? "bg-info" : "bg-warning";

  return (
    <div
      data-testid="inquiry-card"
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      className={`wp-surface-card group relative overflow-hidden rounded-md border bg-bg-elevated pl-6 pr-5 py-5 sm:pl-7 sm:pr-7 sm:py-6 shadow-card transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-border-strong hover:shadow-card-lg ${
        isLatest ? "border-accent/40" : "border-border-default"
      } ${pressed ? "translate-y-0 scale-[0.997] shadow-card" : ""}`}
    >
      {/* Status-keyed accent bar — reads as a case-file tab, giving each
          record a clear at-a-glance category marker even before reading
          the pill text, reinforcing the "structured ledger" identity the
          client asked for over a generic social-post card look. */}
      <span aria-hidden="true" className={`absolute left-0 top-0 h-full w-1 ${accentClass}`} />

      {/* "Latest" marker — real visual-rhythm fix found during a fresh
          audit at realistic scale: a feed of 80+ visually-identical cards
          read as monotonous, not "sharp, minimalist, authoritative." Only
          ever the single most recent record in an unfiltered, newest-first
          view (isLatest is computed by the caller, never guessed from
          card position), so this never misleads on page 2 or under an
          active filter/search. */}
      {isLatest && (
        <span className="absolute right-0 top-0 rounded-bl-md bg-accent px-2.5 py-1 text-[10px] font-mono font-semibold uppercase tracking-[0.1em] text-accent-foreground">
          Latest
        </span>
      )}

      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1">
          <StatusPill status={inquiry.statusTag} />
          {inquiry.isAnonymous ? (
            <span className="inline-flex items-center gap-1 rounded bg-bg-subtle px-2 py-0.5 text-[10px] font-mono text-text-muted border border-border-default/50">
              Anonymous Submission
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded bg-accent/10 px-2 py-0.5 text-[10px] font-mono font-medium text-accent border border-accent/20">
              Verified Inquiry
            </span>
          )}
          <span className="font-mono text-caption tabular-nums text-text-muted">
            {dateLabel}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1 text-caption text-text-muted tabular-nums">
          <MessageSquare className="h-3.5 w-3.5" />
          <span className="inline-block min-w-[1.5ch] text-right">{inquiry.commentCount}</span>
        </div>
      </div>

      <Link
        href={`/inquiries/${inquiry.id}`}
        className="mt-3 block rounded-sm text-h3 font-semibold text-text-primary decoration-accent decoration-1 underline-offset-4 transition-colors hover:text-accent hover:underline focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none [overflow-wrap:anywhere]"
      >
        {inquiry.title}
      </Link>

      <p className="mt-1.5 flex flex-wrap items-center gap-1.5 text-caption text-text-muted">
        <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">
          {metaParts.map((part, i) => (
            <span key={i}>
              {i > 0 && <span aria-hidden="true"> • </span>}
              {part}
            </span>
          ))}
        </span>
        {inquiry.hasAttachments && (
          <span className="inline-flex items-center gap-1 rounded bg-bg-subtle px-2 py-0.5 text-[10px] font-mono text-accent border border-accent/20">
            <Paperclip className="h-3 w-3" />
            <span>Media Evidence Attached</span>
          </span>
        )}
      </p>

      <p className="mt-3 text-body-sm text-text-secondary line-clamp-3 [overflow-wrap:anywhere]">
        {inquiry.description}
      </p>

      <div className="mt-4 flex items-center justify-between gap-3 border-t border-border-default pt-3.5">
        <Link
          href={`/inquiries/${inquiry.id}`}
          className="text-body-sm font-medium text-accent hover:text-accent-hover transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          View Thread &amp; Timeline &rarr;
        </Link>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleFollowClick}
            disabled={followMutation.isPending || unfollowMutation.isPending}
            className={`flex items-center gap-1.5 rounded-sm px-3.5 py-1.5 text-body-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:cursor-not-allowed ${
              inquiry.isFollowing
                ? "bg-accent-subtle text-text-primary hover:bg-accent-subtle/80"
                : "border border-border-strong text-text-primary hover:bg-bg-subtle"
            }`}
          >
            {inquiry.isFollowing ? "Following" : "Follow"}
            <span className="inline-block min-w-[2ch] text-right tabular-nums">
              {inquiry.followerCount}
            </span>
          </button>
          {extraAction}
        </div>
      </div>
    </div>
  );
}
