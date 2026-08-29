"use client";

import { useMutation } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/lib/api-client";

/**
 * Stripe checkout scaffold — AgentGuide/03_MasterPromptGuide.md Step 7.
 * Real backend call, honest about the current state: until the client
 * configures STRIPE_SECRET_KEY/STRIPE_PRICE_ID, the backend returns 501 and
 * this surfaces as a clear "coming soon" message rather than a silent or
 * broken redirect.
 */
export function useCreateCheckoutSession() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ checkoutUrl: string }>("/api/billing/create-checkout-session", {
        method: "POST",
      }),
  });
}

export function isBillingNotConfigured(error: unknown): boolean {
  return error instanceof ApiError && error.status === 501;
}
