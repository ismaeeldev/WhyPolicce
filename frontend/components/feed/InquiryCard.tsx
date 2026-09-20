"use client";

import { MessageSquare, Paperclip } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { StatusPill } from "@/components/feed/StatusPill";
import { useFollowInquiry, useUnfollowInquiry } from "@/hooks/useFollowInquiry";
import type { Inquiry } from "@/hooks/useInquiries";

const dateFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });

/**
 * Home feed inquiry card — forum rebuild, Milestone 2 Step M2.2
 * (WhyPoliceForum_MasterGuide.md). Card shell reuses ThemeGuideline §4.4's
 * existing spec exactly (--bg-elevated, --radius-md, --border hairline,
 * p-6/p-4). Follower/comment counts use tabular-nums in a reserved-width
 * container so a 1->2 digit change never shifts adjacent content
 * (Standing UI Discipline rule 12).
 */
export function InquiryCard({ inquiry }: { inquiry: Inquiry }) {
  const [pressed, setPressed] = useState(false);
  const followMutation = useFollowInquiry();
  const unfollowMutation = useUnfollowInquiry();

  const handleFollowClick = () => {
    if (inquiry.isFollowing) {
      unfollowMutation.mutate(inquiry.id);
    } else {
      followMutation.mutate(inquiry.id);
    }
  };

  const metaParts = [
    dateFormatter.format(new Date(inquiry.createdAt)),
    [inquiry.city, inquiry.state].filter(Boolean).join(", "),
  ];
  if (inquiry.precinct) metaParts.push(inquiry.precinct);

  return (
    <div
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      className={`rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6 shadow-none transition-all duration-150 hover:-translate-y-0.5 hover:shadow-card ${
        pressed ? "translate-y-0 scale-[0.997]" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <StatusPill status={inquiry.statusTag} />
        <div className="flex shrink-0 items-center gap-1 text-caption text-text-muted tabular-nums">
          <MessageSquare className="h-3.5 w-3.5" />
          <span className="inline-block min-w-[1.5ch] text-right">{inquiry.commentCount}</span>
        </div>
      </div>

      <Link
        href={`/inquiries/${inquiry.id}`}
        className="mt-3 block rounded-sm text-body font-medium text-text-primary hover:text-accent transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
      >
        {inquiry.title}
      </Link>

      <p className="mt-1.5 flex flex-wrap items-center gap-x-1.5 text-caption text-text-muted">
        {metaParts.map((part, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <span aria-hidden="true">&middot;</span>}
            {part}
          </span>
        ))}
        {inquiry.hasAttachments && (
          <span className="flex items-center gap-1">
            <span aria-hidden="true">&middot;</span>
            <Paperclip className="h-3 w-3" />
          </span>
        )}
      </p>

      <p className="mt-3 text-body-sm text-text-secondary line-clamp-3 [overflow-wrap:anywhere]">
        {inquiry.description}
      </p>

      <div className="mt-4 flex items-center justify-between gap-3">
        <Link
          href={`/inquiries/${inquiry.id}`}
          className="text-body-sm font-medium text-accent hover:text-accent-hover transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          View Thread &amp; Timeline
        </Link>

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
      </div>
    </div>
  );
}
