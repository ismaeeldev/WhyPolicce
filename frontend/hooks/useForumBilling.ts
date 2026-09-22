"use client";

import { useMutation } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

/**
 * Real Stripe Checkout hooks — forum rebuild, Milestone 3 Step M3.2
 * (WhyPoliceForum_MasterGuide.md). Replaces the TODO placeholders in
 * UpgradeModal.tsx and the attorney portal's subscribe CTA. Both mutations
 * redirect the browser to the real Stripe Checkout URL on success — there
 * is no in-app "success" state to render here, Stripe's own redirect
 * (success_url/cancel_url, set server-side) handles the return trip.
 */
export function useInquiryUpgradeCheckout() {
  return useMutation({
    mutationFn: (inquiryId: string) =>
      apiFetch<{ checkoutUrl: string }>("/api/v1/billing/checkout/inquiry-upgrade", {
        method: "POST",
        body: JSON.stringify({ inquiry_id: inquiryId }),
      }),
    onSuccess: ({ checkoutUrl }) => {
      window.location.href = checkoutUrl;
    },
  });
}

export function useAttorneySubscriptionCheckout() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ checkoutUrl: string }>("/api/v1/billing/checkout/attorney-subscription", {
        method: "POST",
      }),
    onSuccess: ({ checkoutUrl }) => {
      window.location.href = checkoutUrl;
    },
  });
}
