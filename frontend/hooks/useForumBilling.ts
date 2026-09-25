"use client";

import { useMutation } from "@tanstack/react-query";
import { useRef } from "react";

import { ApiError, apiFetch } from "@/lib/api-client";
import { useToastStore } from "@/stores/useToastStore";

/**
 * Real Stripe Checkout hooks — forum rebuild, Milestone 3 Step M3.2
 * (WhyPoliceForum_MasterGuide.md). Replaces the TODO placeholders in
 * UpgradeModal.tsx and the attorney portal's subscribe CTA. Both mutations
 * redirect the browser to the real Stripe Checkout URL on success — there
 * is no in-app "success" state to render here, Stripe's own redirect
 * (success_url/cancel_url, set server-side) handles the return trip.
 *
 * Real gap found during a full-scope re-audit: neither hook had an
 * onError at all — a failed checkout-session creation (501 while
 * Stripe isn't configured yet, or a real Stripe API error once it is)
 * left the button stuck on "Redirecting…" with zero user feedback.
 * Handled here, once, rather than requiring every call site to
 * remember it — same isBillingNotConfigured-style honesty as
 * hooks/useBilling.ts's own established pattern for this exact
 * "billing isn't set up yet" situation.
 */
function isCheckoutNotConfigured(error: unknown): boolean {
  return error instanceof ApiError && error.status === 501;
}

export function useInquiryUpgradeCheckout() {
  const showToast = useToastStore((s) => s.show);
  // Real gap found during a payment-feature audit: disabled={isPending}
  // alone doesn't close the synchronous double-click window — a real
  // double-click (or a fast double-tap on mobile) can fire mutate()
  // twice before React's re-render reflecting isPending=true commits,
  // each creating its own real Stripe Checkout session before the
  // first redirect happens. A plain ref-based lock closes that race
  // immediately, synchronously, on the very first call — matching the
  // exact pattern already established for consequential mutations
  // elsewhere (app/inquiries/new/page.tsx, BecomeAttorneyDialog.tsx).
  const lockRef = useRef(false);
  const mutation = useMutation({
    mutationFn: (inquiryId: string) =>
      apiFetch<{ checkoutUrl: string }>("/api/v1/billing/checkout/inquiry-upgrade", {
        method: "POST",
        body: JSON.stringify({ inquiry_id: inquiryId }),
      }),
    onSuccess: ({ checkoutUrl }) => {
      window.location.href = checkoutUrl;
    },
    onError: (error) => {
      lockRef.current = false;
      showToast(
        isCheckoutNotConfigured(error)
          ? "Upgrades aren't fully set up yet — check back soon."
          : "Couldn't start checkout — try again shortly.",
      );
    },
  });
  return {
    ...mutation,
    mutate: (inquiryId: string) => {
      if (lockRef.current) return;
      lockRef.current = true;
      mutation.mutate(inquiryId);
    },
  };
}

export function useAttorneySubscriptionCheckout() {
  const showToast = useToastStore((s) => s.show);
  const lockRef = useRef(false);
  const mutation = useMutation({
    mutationFn: () =>
      apiFetch<{ checkoutUrl: string }>("/api/v1/billing/checkout/attorney-subscription", {
        method: "POST",
      }),
    onSuccess: ({ checkoutUrl }) => {
      window.location.href = checkoutUrl;
    },
    onError: (error) => {
      lockRef.current = false;
      showToast(
        isCheckoutNotConfigured(error)
          ? "Subscriptions aren't fully set up yet — check back soon."
          : "Couldn't start checkout — try again shortly.",
      );
    },
  });
  return {
    ...mutation,
    mutate: () => {
      if (lockRef.current) return;
      lockRef.current = true;
      mutation.mutate();
    },
  };
}
