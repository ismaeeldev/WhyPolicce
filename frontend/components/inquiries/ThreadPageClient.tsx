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
import { NotFoundContent } from "@/components/shared/NotFoundContent";
import { StatusPill } from "@/components/feed/StatusPill";
import { ThreadSkeleton } from "@/components/inquiries/ThreadSkeleton";
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
  timeZone: "UTC",
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
export function ThreadPageClient() {
  const params = useParams<{ id: string }>();
  const inquiryId = params.id;
  const searchParams = useSearchParams();
  const showToast = useToastStore((s) => s.show);

  const {
    data: inquiry,
    isLoading: inquiryLoading,
    isError: inquiryError,
    error: inquiryErrorObj,
    refetch: refetchInquiry,
  } = useInquiry(inquiryId);
  const {
    data: threadPages,
    isLoading: threadLoading,
    isError: threadError,
    refetch: refetchThread,
    hasNextPage: threadHasNextPage,
    fetchNextPage: fetchNextThreadPage,
    isFetchingNextPage: threadFetchingNextPage,
  } = useThread(inquiryId);
  const thread = threadPages
    ? {
        items: threadPages.pages.flatMap((p) => p.items),
        total: threadPages.pages[0]?.total ?? 0,
      }
    : undefined;
  // Real bug found during a full-scope re-audit: Edit/Delete controls on
  // each comment were rendered completely unconditionally, for every
  // visitor, on every comment — including comments other users wrote.
  // The backend already hard-403s a non-owner's edit/delete (inquiries.py
  // update_comment/delete_comment), so this only ever showed a working-
  // looking pencil/trash icon (complete with a destructive-confirmation
  // dialog on delete) that was guaranteed to fail. authorId is already on
  // each ThreadComment; the backend just never computed a per-comment
  // isAuthor the way it does for the inquiry itself (inquiry.isAuthor),
  // so the backend now sends a per-viewer isAuthor flag on each comment.

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

  if (inquiryLoading || (threadLoading && !inquiryError)) {
    return <ThreadSkeleton />;
  }

  if (inquiryError || !inquiry) {
    // Real bug found during a state-handling audit: this collapsed
    // "the network/backend failed" and "this inquiry was deleted or
    // never existed" into one message with a retry button that can
    // never succeed for the second case — a user following a stale
    // link to a deleted inquiry got a "Try again" they could click
    // forever. A 404 is a genuinely different, permanent outcome from
    // a transient failure; distinguished here via ApiError.status,
    // reusing the app's own real 404 page content instead of a
    // dead-end retry loop.
    const isNotFound = inquiryErrorObj instanceof ApiError && inquiryErrorObj.status === 404;
    if (isNotFound) {
      return <NotFoundContent />;
    }
    // Scope Revision 1 §5.4 — same reasoning as HomeFeedClient's own fix:
    // a pending/rejected attorney's account is server-blocked here, not a
    // transient failure, so no pointless "Try again" retry loop.
    const isUnverifiedAttorney =
      inquiryErrorObj instanceof ApiError && inquiryErrorObj.code === "attorney_not_verified";
    return (
      <div className="mx-auto w-full max-w-[760px] px-5 sm:px-6 py-12 sm:py-16">
        <div className="rounded-md border border-danger bg-danger-subtle p-5 text-center">
          {isUnverifiedAttorney ? (
            <p className="text-body-sm text-text-primary">{inquiryErrorObj.message}</p>
          ) : (
            <>
              <p className="text-body-sm text-text-primary mb-3">This inquiry didn&apos;t load.</p>
              <button
                type="button"
                onClick={() => refetchInquiry()}
                className="rounded-sm px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                Try again
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  // Same fix as InquiryCard's own Follow button: a logged-out visitor
  // clicking Follow used to just flicker (optimistic flip -> silent
  // rollback on the backend's real 401) with no explanation.
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
      {
        onSuccess: () => setEditingCommentId(null),
        onError: (err) => {
          showToast(err instanceof ApiError ? err.message : "Couldn't save that edit. Try again.");
        },
      },
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
          className="group relative rounded-xl border border-border-default/80 bg-bg-elevated/90 backdrop-blur-md p-6 sm:p-8 shadow-card"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-default/60 pb-4">
            <div className="flex items-center gap-2.5">
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
            </div>
            {inquiry.isAuthor && (
              <InquiryEditDeleteControls inquiryId={inquiry.id} onEditClick={() => setEditingInquiry(true)} />
            )}
          </div>

          <div className="mt-5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-accent font-medium">
              Official Inquiry File
            </span>
            <h1 className="font-display text-2xl sm:text-3xl font-semibold text-text-primary mt-1 mb-4 leading-snug [overflow-wrap:anywhere]">
              {inquiry.title}
            </h1>
            <div className="rounded-lg bg-bg-subtle/50 border border-border-default/40 p-4 sm:p-5 text-body text-text-secondary whitespace-pre-wrap leading-relaxed [overflow-wrap:anywhere]">
              {inquiry.description}
            </div>
          </div>

          <p className="mt-4 text-caption font-mono text-text-muted flex flex-wrap items-center gap-2">
            <span>{dateFormatter.format(new Date(inquiry.createdAt))}</span>
            <span>&middot;</span>
            <span>{inquiry.city}, {inquiry.state}</span>
            {inquiry.precinct && (
              <>
                <span>&middot;</span>
                <span className="text-accent">{inquiry.precinct}</span>
              </>
            )}
          </p>

          {inquiry.isAuthor ? (
            <div className="mt-5 pt-4 border-t border-border-default/60">
              <EvidenceUploadField inquiryId={inquiry.id} attachments={inquiry.attachments ?? []} tier={inquiry.tier} />
            </div>
          ) : (
            inquiry.attachments && inquiry.attachments.length > 0 && (
              <div className="mt-5 pt-4 border-t border-border-default/60">
                <AttachmentList attachments={inquiry.attachments} />
              </div>
            )
          )}

          <div className="mt-6 flex flex-wrap items-center gap-3 pt-4 border-t border-border-default/60">
            <button
              type="button"
              onClick={handleFollowClick}
              disabled={followMutation.isPending || unfollowMutation.isPending}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-body-sm font-medium transition-all focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none disabled:cursor-not-allowed ${
                inquiry.isFollowing
                  ? "bg-accent text-accent-foreground shadow-sm"
                  : "border border-border-strong text-text-primary hover:bg-bg-subtle hover:border-accent/40"
              }`}
            >
              {inquiry.isFollowing ? "Following Inquiry" : "Follow Inquiry"}
              <span className="inline-block min-w-[2ch] text-right font-mono tabular-nums text-xs">
                {inquiry.followerCount}
              </span>
            </button>
            <ReportButton targetType="inquiry" targetId={inquiry.id} />
            {inquiry.isAuthor && inquiry.tier === "free" && (
              <button
                type="button"
                onClick={() => setUpgradeModalOpen(true)}
                className="rounded-lg border border-accent/40 bg-accent/10 px-4 py-2 text-body-sm font-medium text-accent hover:bg-accent hover:text-accent-foreground transition-all focus-visible:ring-2 focus-visible:ring-accent outline-none"
              >
                Upgrade this post ($2.99)
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
        {/* Real bug found during a state-handling audit: this always
            rendered "{thread?.total ?? 0} comments" — on a real thread-
            load failure that read as a confident "0 comments" directly
            above the error box below it, when the true count might be
            in the dozens. Only shown once the thread has actually
            loaded. */}
        {!threadError && (
          <p className="mb-3 text-caption font-medium uppercase tracking-wide text-text-muted">
            {thread?.total ?? 0} {thread?.total === 1 ? "comment" : "comments"}
          </p>
        )}

        {threadError && (
          <div className="rounded-md border border-danger bg-danger-subtle p-4 text-center">
            <p className="text-body-sm text-text-primary mb-2">Comments didn&apos;t load.</p>
            <button
              type="button"
              onClick={() => refetchThread()}
              className="rounded-sm px-4 py-2 text-body-sm font-medium text-text-primary hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
            >
              Try again
            </button>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {thread?.items.map((comment) => (
            <div
              key={comment.id}
              className="group flex flex-col gap-2 rounded-xl border border-border-default/80 bg-bg-elevated/90 backdrop-blur-sm p-4 sm:p-5 shadow-sm transition-all duration-200 hover:border-border-strong hover:shadow-card"
            >
              {editingCommentId === comment.id ? (
                <div className="flex flex-col gap-2">
                  <textarea
                    autoFocus
                    value={editDraft}
                    onChange={(e) => setEditDraft(e.target.value)}
                    rows={3}
                    className="w-full rounded-lg border border-border-default bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none resize-none focus:border-accent focus:ring-2 focus:ring-accent/20"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={saveCommentEdit}
                      disabled={updateComment.isPending || !editDraft.trim()}
                      className="rounded-md bg-accent px-3.5 py-1.5 text-caption font-medium text-accent-foreground hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50 transition-colors focus-visible:ring-2 focus-visible:ring-accent outline-none"
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingCommentId(null)}
                      className="text-caption text-text-muted hover:text-text-primary transition-colors px-2 py-1.5 rounded outline-none"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-2 border-b border-border-default/40 pb-2">
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-full bg-accent/15 border border-accent/30 text-accent font-mono text-[10px] font-bold flex items-center justify-center">
                        C
                      </div>
                      <p className="text-caption font-mono text-text-muted">
                        {dateFormatter.format(new Date(comment.createdAt))}
                      </p>
                    </div>
                    {comment.isAuthor && (
                      <CommentEditDeleteControls
                        inquiryId={inquiryId}
                        commentId={comment.id}
                        onEditClick={() => startEditingComment(comment)}
                      />
                    )}
                  </div>
                  <p className="text-body text-text-primary whitespace-pre-wrap leading-relaxed [overflow-wrap:anywhere] pt-1">
                    {comment.body}
                  </p>
                  <div className="flex justify-end pt-1">
                    <ReportButton targetType="thread_comment" targetId={comment.id} />
                  </div>
                </>
              )}
            </div>
          ))}

          {thread && thread.items.length === 0 && !threadError && (
            <div className="rounded-xl border border-dashed border-border-default/80 p-8 text-center bg-bg-elevated/40">
              <p className="text-body-sm text-text-muted">No public statements or community comments recorded yet.</p>
              <p className="text-caption text-text-muted/80 mt-1">Be the first verified advocate or citizen to respond.</p>
            </div>
          )}

          {threadHasNextPage && (
            <button
              type="button"
              onClick={() => fetchNextThreadPage()}
              disabled={threadFetchingNextPage}
              className="self-center rounded-lg border border-border-strong bg-bg-elevated px-5 py-2.5 text-body-sm font-medium text-text-primary transition-all hover:bg-bg-subtle hover:border-accent/40 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-accent outline-none shadow-sm"
            >
              {threadFetchingNextPage ? "Loading…" : "Load more comments"}
            </button>
          )}
        </div>

        {!threadError && (
          <div className="mt-6 rounded-xl border border-border-default/80 bg-bg-elevated p-4 sm:p-5 shadow-card">
            <label htmlFor="comment-input" className="block text-caption font-mono uppercase tracking-wider text-text-muted mb-2">
              Add Statement / Community Trace
            </label>
            <textarea
              id="comment-input"
              value={commentDraft}
              onChange={(e) => setCommentDraft(e.target.value)}
              placeholder="Contribute relevant observations, official records, or timeline updates…"
              rows={3}
              className="w-full rounded-lg border border-border-default bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none resize-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
            {commentError && (
              <div className="mt-2 rounded-lg border border-danger/60 bg-danger-subtle p-3">
                <p className="text-body-sm text-text-primary">{commentError}</p>
              </div>
            )}
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                onClick={handlePostComment}
                disabled={!commentDraft.trim() || createComment.isPending}
                className="rounded-lg bg-accent px-5 py-2.5 text-body-sm font-semibold text-accent-foreground hover:bg-accent-hover disabled:bg-bg-subtle disabled:text-text-muted disabled:cursor-not-allowed transition-all focus-visible:ring-2 focus-visible:ring-accent outline-none shadow-sm"
              >
                {createComment.isPending ? "Submitting…" : "Post Comment"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
