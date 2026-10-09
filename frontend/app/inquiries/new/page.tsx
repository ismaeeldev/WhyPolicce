"use client";

import { useUser } from "@auth0/nextjs-auth0";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { UpgradeModal } from "@/components/inquiries/UpgradeModal";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { ApiError } from "@/lib/api-client";
import { findPrecinctsByNeighborhood, type PrecinctEntry } from "@/lib/nyc-precincts";
import { US_STATES } from "@/lib/us-states";
import { useCreateInquiry } from "@/hooks/useInquiries";
import { useInquiryPublishCheckout } from "@/hooks/useForumBilling";

const EASE = [0.22, 1, 0.36, 1] as const;
const FREE_TIER_CHAR_LIMIT = 250;
// Backend hard caps — backend/app/schemas/inquiry.py's InquiryCreate.
// maxLength on the inputs stops most overlong input at the keystroke,
// but paste can still exceed it in some browsers, so validate() below
// re-checks these explicitly rather than relying on maxLength alone.
const TITLE_MAX_LENGTH = 200;
const CITY_MAX_LENGTH = 200;
const PRECINCT_MAX_LENGTH = 200;

type FieldErrors = {
  title?: string;
  description?: string;
  state?: string;
  city?: string;
  precinct?: string;
};

// Scope Revision 1 §3.2 (AgentGuide/newscoperev1.md) — "deferred sign-up":
// a logged-out visitor can fill this form; the draft is cached here across
// the login/signup interruption and auto-published on return, so they
// never have to retype it. sessionStorage (not localStorage) is
// deliberate — this is meant to be a short-lived draft, not a persistent
// one, and it naturally clears when the tab closes.
const DRAFT_STORAGE_KEY = "whypolice:draft-inquiry";
const DRAFT_MAX_AGE_MS = 30 * 60 * 1000; // 30 minutes — an abandoned draft should not silently auto-publish on a much later visit

type DraftInquiry = {
  title: string;
  description: string;
  state: string;
  city: string;
  precinct: string;
  isAnonymous: boolean;
  savedAt: number;
};

function saveDraft(draft: DraftInquiry) {
  try {
    sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // sessionStorage can throw (private browsing, quota, disabled) — the
    // worst case here is the user has to retype after login, not a crash.
  }
}

function readDraft(): DraftInquiry | null {
  try {
    const raw = sessionStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return null;
    const draft = JSON.parse(raw) as DraftInquiry;
    if (Date.now() - draft.savedAt > DRAFT_MAX_AGE_MS) {
      sessionStorage.removeItem(DRAFT_STORAGE_KEY);
      return null;
    }
    return draft;
  } catch {
    return null;
  }
}

function clearDraft() {
  try {
    sessionStorage.removeItem(DRAFT_STORAGE_KEY);
  } catch {
    // best-effort — see saveDraft's comment
  }
}

/**
 * New inquiry form — forum rebuild, Milestone 2 Step M2.3
 * (WhyPoliceForum_MasterGuide.md). The core citizen write-action and the
 * first place the $2.99 micro-upgrade becomes a real, visible product
 * experience.
 *
 * State list is a real, complete US-states-plus-DC static reference
 * (lib/us-states.ts, built in M2.2) — deliberately NOT the old product's
 * supported_states()/useSupportedStates, which only covers the ~32
 * states the old RAG product had ingested data for. Reusing that here
 * would silently block a citizen in any of the other ~18 states from
 * posting at all, directly contradicting the scope PDF's "nationwide
 * from day one" requirement.
 */
export default function NewInquiryPage() {
  const router = useRouter();
  const createInquiry = useCreateInquiry();
  const publishCheckout = useInquiryPublishCheckout();
  const { user, isLoading: userLoading } = useUser();

  // §3.2 — a cached draft (if present and not stale) initializes the form
  // synchronously on first render via useState's lazy initializer, rather
  // than being restored later inside an effect (which would require
  // several setState calls in a row, an anti-pattern that also can't
  // synchronously trigger the auto-submit below in the same tick).
  const [initialDraft] = useState<DraftInquiry | null>(() => readDraft());
  const [title, setTitle] = useState(() => initialDraft?.title ?? "");
  const [description, setDescription] = useState(() => initialDraft?.description ?? "");
  const [state, setState] = useState(() => initialDraft?.state ?? "");
  const [city, setCity] = useState(() => initialDraft?.city ?? "");
  const [precinct, setPrecinct] = useState(() => initialDraft?.precinct ?? "");
  // Scope Revision 1 §4.3 — "Post Anonymously to Public Feed" checkbox.
  const [isAnonymous, setIsAnonymous] = useState(() => initialDraft?.isAnonymous ?? false);
  // Scope Revision 1 §4.2 — minimal NYC-only precinct helper. Client's own
  // wording had no stated city scope or accuracy bar ("a lightweight
  // location auto-complete or lookup tool"), so this starts as the
  // smallest reasonable interpretation: a neighborhood-name lookup
  // against NYPD's own precinct directory (already verified elsewhere in
  // this codebase — see lib/nyc-precincts.ts's own docstring), only shown
  // when state=NY, with no new external API or cost. Nationwide/exact-GIS
  // coverage is explicitly out of scope for this first pass.
  const [precinctSearch, setPrecinctSearch] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);

  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const charCount = description.length;
  const overLimit = charCount > FREE_TIER_CHAR_LIMIT;

  const precinctMatches: PrecinctEntry[] =
    state === "NY" ? findPrecinctsByNeighborhood(precinctSearch) : [];

  // Real double-submit guard, per M2.3's own Bug Fix requirement: a
  // double-click can fire two submit events before React's re-render
  // (driven by createInquiry.isPending) has actually disabled the
  // button, since state updates aren't synchronous. A plain ref-based
  // lock closes that race window immediately, synchronously, on the
  // very first submit — disabled={createInquiry.isPending} alone is
  // not sufficient to prevent this class of double-submit.
  const submitLockRef = useRef(false);

  const validate = (): FieldErrors => {
    const errors: FieldErrors = {};
    if (!title.trim()) errors.title = "Title is required.";
    else if (title.length > TITLE_MAX_LENGTH) errors.title = `Title must be ${TITLE_MAX_LENGTH} characters or fewer.`;
    if (!description.trim()) errors.description = "Description is required.";
    if (!state) errors.state = "State is required.";
    if (!city.trim()) errors.city = "City is required.";
    else if (city.length > CITY_MAX_LENGTH) errors.city = `City must be ${CITY_MAX_LENGTH} characters or fewer.`;
    if (precinct.length > PRECINCT_MAX_LENGTH) errors.precinct = `Precinct must be ${PRECINCT_MAX_LENGTH} characters or fewer.`;
    return errors;
  };

  const submitInquiry = () => {
    createInquiry.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        state,
        city: city.trim(),
        precinct: precinct.trim() || undefined,
        isAnonymous,
      },
      {
        onSuccess: (created) => {
          clearDraft(); // §3.2 step 4 — never resurface on a later, unrelated visit
          router.push(`/inquiries/${created.id}`);
        },
        onError: (err) => {
          submitLockRef.current = false;
          setSubmitError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        },
      },
    );
  };

  // Shared by the manual Publish click AND §3.2's post-login auto-submit —
  // deliberately the single path both go through, so validation (the
  // 250-char free-tier check in particular) can never be bypassed by the
  // automated resubmit. `overLimit` is read fresh from the description arg
  // rather than closed-over state, since the auto-submit path calls this
  // synchronously in the same tick it sets state via setDescription, before
  // a re-render would have updated the closure's `overLimit`/`charCount`.
  const attemptSubmit = (currentDescription: string) => {
    if (submitLockRef.current) return;

    setSubmitError(null);
    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    // Real Bug Fix scenario, handled explicitly (WhyPoliceForum_
    // MasterGuide.md M2.3): a paste event can add 5000 characters in one
    // change, not one keystroke at a time — this check runs against the
    // CURRENT description value on every submit attempt, never assuming
    // an onKeyPress-driven counter kept up incrementally, so a pasted
    // overlong value is caught here identically to a typed one. This
    // branch doesn't actually submit anything yet, so it must NOT hold
    // the double-submit lock — the user needs to be able to try
    // submitting again after dismissing the modal (e.g. via "Trim my
    // post instead").
    if (currentDescription.length > FREE_TIER_CHAR_LIMIT) {
      setUpgradeModalOpen(true);
      return;
    }

    submitLockRef.current = true;
    submitInquiry();
  };

  // §3.2 step 3 — auto-publish once, on return from login/signup, if the
  // form was restored from a cached draft. Waits for auth state to
  // resolve (userLoading) so this never fires before we actually know
  // whether the user is logged in. Guarded by a ref so a re-render (e.g.
  // React Query refetch) can never trigger a second, duplicate publish.
  const autoSubmitAttemptedRef = useRef(false);
  useEffect(() => {
    if (!initialDraft || userLoading || !user || autoSubmitAttemptedRef.current) return;
    autoSubmitAttemptedRef.current = true;
    attemptSubmit(description);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally runs once, gated by autoSubmitAttemptedRef, not on every dependency change
  }, [user, userLoading]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!user) {
      // §3.2 — deferred sign-up: cache the draft, then hand off to the
      // existing /login?returnTo= pattern already used everywhere else in
      // this app (proxy.ts generates this exact URL shape for every other
      // protected route) rather than inventing a new auth-entry scheme.
      saveDraft({ title, description, state, city, precinct, isAnonymous, savedAt: Date.now() });
      router.push(`/login?returnTo=${encodeURIComponent("/inquiries/new")}`);
      return;
    }
    attemptSubmit(description);
  };

  const handleTrimInstead = () => {
    // Deliberately does NOT clear or truncate the textarea — the user
    // must be able to see and edit their own full original text down
    // themselves (M2.3's own explicit requirement), never silently cut.
    descriptionRef.current?.focus();
  };

  // Scope Revision 2 §4.1 Option A — "Pay $2.99 to Publish Full Post".
  // Re-validates the rest of the form (title/state/city/etc.) exactly
  // like the normal Publish path — the modal only ever opens because
  // the description was over the limit, but every OTHER field still
  // needs to be valid before creating a real row. Creates the inquiry
  // as pending_payment, then immediately starts its Stripe Checkout with
  // the id the backend just returned; on any failure here the pending
  // row still exists (visible only to its author via My Inquiries) so
  // nothing is lost, they can just retry from the modal again.
  const handlePayToPublish = () => {
    if (!user) return;
    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    setSubmitError(null);
    createInquiry.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        state,
        city: city.trim(),
        precinct: precinct.trim() || undefined,
        isAnonymous,
        acceptPendingPayment: true,
      },
      {
        onSuccess: (created) => {
          clearDraft();
          publishCheckout.mutate(created.id);
        },
        onError: (err) => {
          setSubmitError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        },
      },
    );
  };

  return (
    <div className="mx-auto w-full max-w-[720px] px-4 sm:px-6 py-10 sm:py-14">
      <div className="mb-8">
        <div className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/15 px-3 py-0.5 text-[11px] font-mono font-medium uppercase tracking-[0.14em] text-accent mb-3 backdrop-blur-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          Civic Incident Intake
        </div>
        <motion.h1
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: EASE }}
          className="font-display text-3xl sm:text-4xl font-semibold text-text-primary tracking-tight"
        >
          Submit Public Inquiry
        </motion.h1>
        <p className="mt-2 text-body-sm text-text-secondary">
          Post an incident summary to request public accountability, community corroboration, or licensed legal review.
        </p>
      </div>

      <motion.form
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05, ease: EASE }}
        onSubmit={handleSubmit}
        noValidate
        className="flex flex-col gap-6 rounded-2xl border border-border-default/80 bg-bg-elevated/90 backdrop-blur-md p-6 sm:p-8 shadow-card-lg"
      >
        <div>
          <label htmlFor="title" className="mb-1.5 block text-caption font-mono uppercase tracking-wider text-text-secondary font-medium">
            Incident Headline / Title *
          </label>
          <input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={TITLE_MAX_LENGTH}
            placeholder="e.g. Unreasonable search during routine traffic stop"
            className={`h-11 w-full rounded-lg border bg-bg px-3.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
              fieldErrors.title ? "border-danger" : "border-border-default"
            }`}
          />
          <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{fieldErrors.title}</p>
        </div>

        <div>
          <label htmlFor="description" className="mb-1.5 block text-caption font-mono uppercase tracking-wider text-text-secondary font-medium">
            Incident Description &amp; Details *
          </label>
          <textarea
            id="description"
            ref={descriptionRef}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={6}
            placeholder="Describe what occurred with as much factual detail, time sequence, and officer statements as possible…"
            className={`w-full rounded-lg border bg-bg px-3.5 py-2.5 text-body text-text-primary outline-none resize-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
              fieldErrors.description ? "border-danger" : "border-border-default"
            }`}
          />
          <div className="mt-1 flex items-center justify-between gap-2">
            <p className="min-h-[1.25rem] text-caption text-danger">{fieldErrors.description}</p>
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-24 rounded-full bg-bg-subtle overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    overLimit ? "bg-warning" : "bg-accent"
                  }`}
                  style={{ width: `${Math.min(100, (charCount / FREE_TIER_CHAR_LIMIT) * 100)}%` }}
                />
              </div>
              <p className={`shrink-0 text-caption font-mono tabular-nums ${overLimit ? "text-warning font-semibold" : "text-text-muted"}`}>
                {charCount}/{FREE_TIER_CHAR_LIMIT}
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="state" className="mb-1.5 block text-body-sm text-text-secondary">
              State
            </label>
            <Select
              value={state}
              onValueChange={(value) => setState(value as string)}
            >
              <SelectTrigger
                id="state"
                className={fieldErrors.state ? "border-danger" : undefined}
              >
                <SelectValue placeholder="Select a state">
                  {(value: string) => US_STATES.find((s) => s.code === value)?.name ?? value}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {US_STATES.map((s) => (
                  <SelectItem key={s.code} value={s.code}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{fieldErrors.state}</p>
          </div>

          <div>
            <label htmlFor="city" className="mb-1.5 block text-body-sm text-text-secondary">
              City
            </label>
            <input
              id="city"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              maxLength={CITY_MAX_LENGTH}
              className={`h-11 w-full rounded-sm border bg-bg-elevated px-3.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
                fieldErrors.city ? "border-danger" : "border-border-default"
              }`}
            />
            <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{fieldErrors.city}</p>
          </div>
        </div>

        <div>
          <label htmlFor="precinct" className="mb-1.5 block text-body-sm text-text-secondary">
            Precinct <span className="text-text-muted">(optional)</span>
          </label>
          <input
            id="precinct"
            value={precinct}
            onChange={(e) => setPrecinct(e.target.value)}
            maxLength={PRECINCT_MAX_LENGTH}
            className={`h-11 w-full rounded-sm border bg-bg-elevated px-3.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
              fieldErrors.precinct ? "border-danger" : "border-border-default"
            }`}
          />
          <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{fieldErrors.precinct}</p>

          {state === "NY" && (
            <div className="mt-2">
              <label htmlFor="precinct-helper" className="mb-1.5 block text-caption text-text-muted">
                Don&apos;t know your precinct? Type your NYC neighborhood:
              </label>
              <input
                id="precinct-helper"
                value={precinctSearch}
                onChange={(e) => setPrecinctSearch(e.target.value)}
                placeholder="e.g. Harlem, Park Slope, Astoria..."
                className="h-10 w-full rounded-sm border border-border-default bg-bg px-3 text-body-sm text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20"
              />
              {precinctMatches.length > 0 && (
                <ul className="mt-1.5 flex flex-col gap-1 rounded-sm border border-border-default bg-bg-elevated p-1.5">
                  {precinctMatches.map((match) => (
                    <li key={match.precinct}>
                      <button
                        type="button"
                        onClick={() => {
                          setPrecinct(match.precinct);
                          setPrecinctSearch("");
                        }}
                        className="w-full rounded-sm px-2.5 py-1.5 text-left text-body-sm text-text-primary transition-colors hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                      >
                        Precinct {match.precinct}
                        <span className="text-text-muted"> — {match.neighborhoods}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {precinctSearch.trim().length >= 2 && precinctMatches.length === 0 && (
                <p className="mt-1.5 text-caption text-text-muted">
                  No match found — this covers a limited set of NYC neighborhoods for now, so it&apos;s fine to leave precinct blank or enter it yourself if you know it.
                </p>
              )}
            </div>
          )}
        </div>

        <label className="flex items-center gap-2.5 text-body-sm text-text-secondary">
          <Checkbox
            checked={isAnonymous}
            onCheckedChange={(checked) => setIsAnonymous(checked === true)}
          />
          Post Anonymously to Public Feed
        </label>

        {submitError && (
          <div className="rounded-md border border-danger bg-danger-subtle p-4">
            <p className="text-body-sm text-text-primary">{submitError}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={createInquiry.isPending}
          className="mt-2 h-11 rounded-sm bg-accent px-4 text-body-sm font-medium text-accent-foreground transition-colors hover:bg-accent-hover disabled:bg-bg-subtle disabled:text-text-muted disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          {createInquiry.isPending ? "Posting…" : "Post Inquiry"}
        </button>
      </motion.form>

      <UpgradeModal
        open={upgradeModalOpen}
        onOpenChange={setUpgradeModalOpen}
        title="This post exceeds 250 characters"
        description="Free posts are capped at 250 characters. You can either trim your text to post for free, or complete the one-time $2.99 upgrade now to publish your full text and unlock heavy attachments."
        secondaryAction={{ label: "Trim Text Instead", onClick: handleTrimInstead }}
        primaryAction={{
          label: "Pay $2.99 to Publish Full Post",
          onClick: handlePayToPublish,
          isPending: createInquiry.isPending || publishCheckout.isPending,
        }}
        descriptionTextareaRef={descriptionRef}
      />
    </div>
  );
}
