/**
 * Attorney subscription placeholder — forum rebuild, Milestone 2 Step
 * M2.4 (WhyPoliceForum_MasterGuide.md). No real backend field exists
 * yet for "attorney subscription active" (confirmed: User model has
 * `tier` for the citizen $2.99/Stripe flow and `verification_status`
 * for bar approval, neither of which represents a paid attorney
 * subscription) — Milestone 3 wires the real $149/month Stripe
 * subscription check.
 *
 * Matches this codebase's own established honesty pattern for exactly
 * this situation (see hooks/useBilling.ts's isBillingNotConfigured) —
 * this MUST stay a real, named, always-false stub, never an
 * always-true placeholder that could be mistaken for real gating.
 */
export const ATTORNEY_SUBSCRIPTION_ACTIVE_STUB = false;
