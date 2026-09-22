"use client";

import { motion } from "framer-motion";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AttachmentList } from "@/components/inquiries/AttachmentList";
import { CommentEditDeleteControls } from "@/components/inquiries/CommentEditDeleteControls";
import { ConsultationRequestRow } from "@/components/inquiries/ConsultationRequestRow";
import { EvidenceUploadField } from "@/components/inquiries/EvidenceUploadField";
import { InquiryEditDeleteControls } from "@/components/inquiries/InquiryEditDeleteControls";
import { InquiryEditForm } from "@/components/inquiries/InquiryEditForm";
import { ReportButton } from "@/components/inquiries/ReportButton";
import { UpgradeModal } from "@/components/inquiries/UpgradeModal";
import { StatusPill } from "@/components/feed/StatusPill";
import { ApiError } from "@/lib/api-client";
import { useFollowInquiry, useUnfollowInquiry } from "@/hooks/useFollowInquiry";
import { useInquiryUpgradeCheckout } from "@/hooks/useForumBilling";
import { useToastStore } from "@/stores/useToastStore";
import {
  useCreateComment,
  useInquiry,
  useThread,
  useUpdateComment,
  type ThreadComment,
} from "@/hooks/useInquiries";

const EASE = [0.22, 1, 0.36, 1] as const;
const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

/**
 * Thread & Timeline page — forum rebuild, Milestone 2 Step M2.4
 * (WhyPoliceForum_MasterGuide.md). Fetches the inquiry's own full
 * detail SEPARATELY from its comment thread (M1.4's own resolved
 * ambiguity: these are two different endpoints, not one combined
 * response) — never reads from the feed's cached/truncated preview
 * data, since this needs the full untruncated description regardless
 * of tier.
 *
 * Layout adapts the old SessionDetailPage's exact "You asked" eyebrow +
 * border-l-2 border-accent/40 quoted-content visual language for "the
 * original inquiry" vs. thread comments, rather than inventing new
 * visual grammar for the same underlying pattern.
 */
export default function ThreadPage() {
  const params = useParams<{ id: string }>();
  const inquiryId = params.id;
  const searchParams = useSearchParams();
  const showToast = useToastStore((s) => s.show);

  const { data: inquiry, isLoading: inquiryLoading, isError: inquiryError, refetch: refetchInquiry } =
    useInquiry(inquiryId);
  const { data: thread, isLoading: threadLoading, isError: threadError, refetch: refetchThread } =
    useThread(inquiryId);

  const [editingInquiry, setEditingInquiry] = useState(false);
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [commentDraft, setCommentDraft] = useState("");
  const [editDraft, setEditDraft] = useState("");
  const [commentError, setCommentError] = useState<string | null>(null);
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);
  const inquiryUpgradeCheckout = useInquiryUpgradeCheckout();

  // Real M3.2 post-checkout return handling — same ?upgraded=1 + refetch +
  // toast + clean-URL pattern already established by the old AccountPage's
  // own post-checkout handling, not a new convention for this one screen.
  useEffect(() => {
    if (searchParams.get("upgraded") !== "1") return;
    void refetchInquiry();
    showToast("Upgrade complete — your post is now unlocked.");
    window.history.replaceState({}, "", `/inquiries/${inquiryId}`);
  }, [searchParams, refetchInquiry, showToast, inquiryId]);

  const followMutation = useFollowInquiry();
  const unfollowMutation = useUnfollowInquiry();
  const createComment = useCreateComment(inquiryId);
  const updateComment = useUpdateComment(inquiryId);

  if (inquiryLoading || threadLoading) {
    return (
      <div className="mx-auto w-full max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
        <div className="animate-pulse">
          <div className="h-5 w-32 rounded-full bg-bg-subtle" />
          <div className="mt-4 h-8 w-3/4 rounded bg-bg-subtle" />
          <div className="mt-6 h-24 w-full rounded bg-bg-subtle" />
        </div>
      </div>
    );
  }

  if (inquiryError || !inquiry) {
    return (
      <div className="mx-auto w-full max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
        <div className="rounded-md border border-danger bg-danger-subtle p-5 text-center">
          <p className="text-body-sm text-text-primary mb-3">This inquiry didn&apos;t load.</p>
          <button
            type="button"
            onClick={() => refetchInquiry()}
            className="rounded-sm px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  const handleFollowClick = () => {
    if (inquiry.isFollowing) {
      unfollowMutation.mutate(inquiry.id);
    } else {
      followMutation.mutate(inquiry.id);
    }
  };

  const handlePostComment = () => {
    if (!commentDraft.trim()) return;
    setCommentError(null);
    createComment.mutate(commentDraft.trim(), {
      onSuccess: () => setCommentDraft(""),
      onError: (err) => {
        setCommentError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      },
    });
  };

  const startEditingComment = (comment: ThreadComment) => {
    setEditingCommentId(comment.id);
    setEditDraft(comment.body);
  };

  const saveCommentEdit = () => {
    if (!editingCommentId || !editDraft.trim()) return;
    updateComment.mutate(
      { commentId: editingCommentId, body: editDraft.trim() },
      { onSuccess: () => setEditingCommentId(null) },
    );
  };

  return (
    <div className="mx-auto w-full max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
      {editingInquiry ? (
        <InquiryEditForm
          inquiry={inquiry}
          onCancel={() => setEditingInquiry(false)}
          onSaved={() => setEditingInquiry(false)}
        />
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: EASE }}
          className="group relative rounded-md border border-border-default bg-bg-elevated p-4 sm:p-6"
        >
          {inquiry.isAuthor && (
            <InquiryEditDeleteControls inquiryId={inquiry.id} onEditClick={() => setEditingInquiry(true)} />
          )}

          <div className="flex items-center justify-between gap-3">
            <StatusPill status={inquiry.statusTag} />
          </div>

          <p className="mt-4 mb-1.5 text-caption font-medium uppercase tracking-wide text-text-muted">
            The original inquiry
          </p>
          <h1 className="border-l-2 border-accent/40 pl-3 text-h3 font-semibold text-text-primary">
            {inquiry.title}
          </h1>
          <p className="mt-3 border-l-2 border-accent/40 pl-3 text-body text-text-secondary whitespace-pre-wrap [overflow-wrap:anywhere]">
            {inquiry.description}
          </p>

          <p className="mt-4 text-caption text-text-muted">
            {dateFormatter.format(new Date(inquiry.createdAt))} &middot; {inquiry.city}, {inquiry.state}
            {inquiry.precinct ? ` · ${inquiry.precinct}` : ""}
          </p>

          {inquiry.isAuthor ? (
            <div className="mt-4">
              <EvidenceUploadField inquiryId={inquiry.id} attachments={inquiry.attachments ?? []} />
            </div>
          ) : (
            inquiry.attachments && inquiry.attachments.length > 0 && (
              <div className="mt-4">
                <AttachmentList attachments={inquiry.attachments} />
              </div>
            )
          )}

          <div className="mt-4 flex items-center gap-3">
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
            <ReportButton targetType="inquiry" targetId={inquiry.id} />
            {inquiry.isAuthor && inquiry.tier === "free" && (
              <button
                type="button"
                onClick={() => setUpgradeModalOpen(true)}
                className="rounded-sm border border-border-strong px-3.5 py-1.5 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                Upgrade this post
              </button>
            )}
          </div>
        </motion.div>
      )}

      {inquiry.isAuthor && inquiry.tier === "free" && (
        <UpgradeModal
          open={upgradeModalOpen}
          onOpenChange={setUpgradeModalOpen}
          title="Upgrade this post for $2.99"
          description="Unlock the full 250+ character length for this inquiry with a one-time $2.99 payment."
          primaryAction={{
            label: "Upgrade for $2.99",
            onClick: () => inquiryUpgradeCheckout.mutate(inquiry.id),
            isPending: inquiryUpgradeCheckout.isPending,
          }}
        />
      )}

      {inquiry.isAuthor && inquiry.attorneyRequests && inquiry.attorneyRequests.length > 0 && (
        <div className="mt-6">
          <p className="mb-2 text-caption font-medium uppercase tracking-wide text-text-muted">
            Attorney requests
          </p>
          <div className="flex flex-col gap-2">
            {inquiry.attorneyRequests.map((request) => (
              <ConsultationRequestRow key={request.id} request={request} inquiryId={inquiry.id} />
            ))}
          </div>
        </div>
      )}

      <div className="mt-8">
        <p className="mb-3 text-caption font-medium uppercase tracking-wide text-text-muted">
          {thread?.total ?? 0} {thread?.total === 1 ? "comment" : "comments"}
        </p>

        {threadError && (
          <div className="rounded-md border border-danger bg-danger-subtle p-4 text-center">
            <p className="text-body-sm text-text-primary mb-2">Comments didn&apos;t load.</p>
            <button
              type="button"
              onClick={() => refetchThread()}
              className="text-body-sm font-medium text-text-primary hover:underline"
            >
              Try again
            </button>
          </div>
        )}

        <div className="flex flex-col gap-4">
          {thread?.items.map((comment) => (
            <div key={comment.id} className="group flex flex-col gap-1">
              {editingCommentId === comment.id ? (
                <div className="flex flex-col gap-2">
                  <textarea
                    autoFocus
                    value={editDraft}
                    onChange={(e) => setEditDraft(e.target.value)}
                    rows={3}
                    className="w-full rounded-sm border border-border-default bg-bg-elevated px-3.5 py-2.5 text-body text-text-primary outline-none resize-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={saveCommentEdit}
                      disabled={updateComment.isPending || !editDraft.trim()}
                      className="rounded-sm bg-accent px-3 py-1.5 text-caption font-medium text-accent-foreground hover:bg-accent-hover disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingCommentId(null)}
                      className="text-caption text-text-muted hover:text-text-primary transition-colors rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-caption text-text-muted">
                      {dateFormatter.format(new Date(comment.createdAt))}
                    </p>
                    <CommentEditDeleteControls
                      inquiryId={inquiryId}
                      commentId={comment.id}
                      onEditClick={() => startEditingComment(comment)}
                    />
                  </div>
                  <p className="text-body text-text-primary whitespace-pre-wrap [overflow-wrap:anywhere]">
                    {comment.body}
                  </p>
                  <ReportButton targetType="thread_comment" targetId={comment.id} />
                </>
              )}
            </div>
          ))}

          {thread && thread.items.length === 0 && !threadError && (
            <p className="text-body-sm text-text-muted">No comments yet. Be the first to reply.</p>
          )}
        </div>

        <div className="mt-6">
          <textarea
            value={commentDraft}
            onChange={(e) => setCommentDraft(e.target.value)}
            placeholder="Add a comment…"
            rows={3}
            className="w-full rounded-sm border border-border-default bg-bg-elevated px-3.5 py-2.5 text-body text-text-primary outline-none resize-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20"
          />
          {commentError && (
            <div className="mt-2 rounded-md border border-danger bg-danger-subtle p-3">
              <p className="text-body-sm text-text-primary">{commentError}</p>
            </div>
          )}
          <button
            type="button"
            onClick={handlePostComment}
            disabled={!commentDraft.trim() || createComment.isPending}
            className="mt-2 rounded-sm bg-accent px-4 py-2 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover disabled:bg-bg-subtle disabled:text-text-muted disabled:cursor-not-allowed transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            {createComment.isPending ? "Posting…" : "Post Comment"}
          </button>
        </div>
      </div>
    </div>
  );
}
