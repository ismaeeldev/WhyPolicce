"use client";

import { useMutation } from "@tanstack/react-query";

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
  return useMutation({
    mutationFn: (inquiryId: string) =>
      apiFetch<{ checkoutUrl: string }>("/api/v1/billing/checkout/inquiry-upgrade", {
        method: "POST",
        body: JSON.stringify({ inquiry_id: inquiryId }),
      }),
    onSuccess: ({ checkoutUrl }) => {
      window.location.href = checkoutUrl;
    },
    onError: (error) => {
      showToast(
        isCheckoutNotConfigured(error)
          ? "Upgrades aren't fully set up yet — check back soon."
          : "Couldn't start checkout — try again shortly.",
      );
    },
  });
}

export function useAttorneySubscriptionCheckout() {
  const showToast = useToastStore((s) => s.show);
  return useMutation({
    mutationFn: () =>
      apiFetch<{ checkoutUrl: string }>("/api/v1/billing/checkout/attorney-subscription", {
        method: "POST",
      }),
    onSuccess: ({ checkoutUrl }) => {
      window.location.href = checkoutUrl;
    },
    onError: (error) => {
      showToast(
        isCheckoutNotConfigured(error)
          ? "Subscriptions aren't fully set up yet — check back soon."
          : "Couldn't start checkout — try again shortly.",
      );
    },
  });
}
