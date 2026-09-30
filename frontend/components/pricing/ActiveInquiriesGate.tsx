"use client";

import { useUser } from "@auth0/nextjs-auth0";

import { ActiveInquiriesPanel } from "@/components/pricing/ActiveInquiriesPanel";

/**
 * Gates "Your Active Inquiries" (Scope Revision 2 §3.1) on a real,
 * logged-in session — same useUser() check PricingCards.tsx already
 * uses. Not rendered at all for a logged-out visitor (not an empty
 * state — genuinely absent), per the client's own "For Logged-In
 * Citizens" wording. Split out from ActiveInquiriesPanel itself so the
 * panel component stays free of auth-gating logic.
 */
export function ActiveInquiriesGate() {
  const { user, isLoading } = useUser();

  if (isLoading || !user) return null;

  return <ActiveInquiriesPanel />;
}
