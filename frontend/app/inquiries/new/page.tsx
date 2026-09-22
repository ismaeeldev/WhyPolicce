"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { StatusTagSelector } from "@/components/inquiries/StatusTagSelector";
import { UpgradeModal } from "@/components/inquiries/UpgradeModal";
import type { StatusTag } from "@/components/feed/StatusPill";
import { ApiError } from "@/lib/api-client";
import { US_STATES } from "@/lib/us-states";
import { useCreateInquiry } from "@/hooks/useInquiries";

const EASE = [0.22, 1, 0.36, 1] as const;
const FREE_TIER_CHAR_LIMIT = 250;

type FieldErrors = {
  title?: string;
  description?: string;
  state?: string;
  city?: string;
  statusTag?: string;
};

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

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [state, setState] = useState("");
  const [city, setCity] = useState("");
  const [precinct, setPrecinct] = useState("");
  const [statusTag, setStatusTag] = useState<StatusTag | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [upgradeModalOpen, setUpgradeModalOpen] = useState(false);

  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const charCount = description.length;
  const overLimit = charCount > FREE_TIER_CHAR_LIMIT;

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
    if (!description.trim()) errors.description = "Description is required.";
    if (!state) errors.state = "State is required.";
    if (!city.trim()) errors.city = "City is required.";
    if (!statusTag) errors.statusTag = "Please select a status.";
    return errors;
  };

  const submitInquiry = () => {
    if (!statusTag) return;
    createInquiry.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        state,
        city: city.trim(),
        precinct: precinct.trim() || undefined,
        statusTag,
      },
      {
        onSuccess: (created) => {
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

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
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
    if (overLimit) {
      setUpgradeModalOpen(true);
      return;
    }

    submitLockRef.current = true;
    submitInquiry();
  };

  const handleTrimInstead = () => {
    // Deliberately does NOT clear or truncate the textarea — the user
    // must be able to see and edit their own full original text down
    // themselves (M2.3's own explicit requirement), never silently cut.
    descriptionRef.current?.focus();
  };

  return (
    <div className="mx-auto w-full max-w-[640px] px-5 sm:px-6 py-12 sm:py-16">
      <motion.h1
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: EASE }}
        className="font-display text-h1 text-text-primary mb-8"
      >
        New Inquiry
      </motion.h1>

      <motion.form
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.05, ease: EASE }}
        onSubmit={handleSubmit}
        noValidate
        className="flex flex-col gap-5 rounded-md border border-border-default bg-bg-elevated p-5 sm:p-7 shadow-card"
      >
        <div>
          <label htmlFor="title" className="mb-1.5 block text-body-sm text-text-secondary">
            Title
          </label>
          <input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={`h-11 w-full rounded-sm border bg-bg-elevated px-3.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
              fieldErrors.title ? "border-danger" : "border-border-default"
            }`}
          />
          <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{fieldErrors.title}</p>
        </div>

        <div>
          <label htmlFor="description" className="mb-1.5 block text-body-sm text-text-secondary">
            Description
          </label>
          <textarea
            id="description"
            ref={descriptionRef}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={6}
            className={`w-full rounded-sm border bg-bg-elevated px-3.5 py-2.5 text-body text-text-primary outline-none resize-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20 ${
              fieldErrors.description ? "border-danger" : "border-border-default"
            }`}
          />
          <div className="mt-1 flex items-start justify-between gap-2">
            <p className="min-h-[1.25rem] text-caption text-danger">{fieldErrors.description}</p>
            {/* Plain page-background counter text, not on a colored chip
                — the §1.4 warning-on-warning-subtle contrast concern only
                applies to text sitting ON --warning-subtle, which this
                isn't, so --warning text here is genuinely safe. */}
            <p className={`shrink-0 text-caption tabular-nums ${overLimit ? "text-warning" : "text-text-muted"}`}>
              {charCount}/{FREE_TIER_CHAR_LIMIT}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="state" className="mb-1.5 block text-body-sm text-text-secondary">
              State
            </label>
            <select
              id="state"
              value={state}
              onChange={(e) => setState(e.target.value)}
              className={`h-11 w-full rounded-sm border bg-bg-elevated px-3 text-body text-text-primary outline-none focus:border-accent ${
                fieldErrors.state ? "border-danger" : "border-border-default"
              }`}
            >
              <option value="">Select a state</option>
              {US_STATES.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.name}
                </option>
              ))}
            </select>
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
            className="h-11 w-full rounded-sm border border-border-default bg-bg-elevated px-3.5 text-body text-text-primary outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20"
          />
        </div>

        <div>
          <StatusTagSelector value={statusTag} onChange={setStatusTag} />
          <p className="mt-1 min-h-[1.25rem] text-caption text-danger">{fieldErrors.statusTag}</p>
        </div>

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
        onTrimInstead={handleTrimInstead}
        descriptionTextareaRef={descriptionRef}
      />
    </div>
  );
}
