/**
 * Isomorphic (no "use client") feed query building blocks — split out of
 * hooks/useInquiries.ts specifically so app/page.tsx's Server Component
 * can call fetchInquiriesPage/inquiriesQueryKey directly to prefetch the
 * feed's first page. Everything in useInquiries.ts is implicitly
 * client-only once that file has "use client" at the top, even a plain
 * helper function with no hooks in it — Next.js refuses to let a Server
 * Component call it at all. This file has no such marker, so it's safe
 * from both sides; useInquiries.ts re-exports everything here so none of
 * its existing importers need to change.
 */
import { apiFetch } from "@/lib/api-client";
import type { Inquiry } from "@/hooks/useInquiries";

// Injectable fetcher — the client path uses apiFetch (Auth0's client
// getAccessToken helper), the server prefetch path (app/page.tsx) uses
// serverApiFetch (lib/api-server-fetch.ts, Auth0Client.getAccessToken())
// instead. Not imported directly here: importing lib/api-server-fetch.ts
// (which imports lib/auth0.ts, a real Auth0Client with server secrets)
// from a file reachable by client bundles would be a real problem even
// if never called client-side — dead-code elimination isn't a security
// boundary to rely on for secrets.
type Fetcher = <T>(path: string) => Promise<T>;

export type InquiriesPage = {
  items: Inquiry[];
  total: number;
  limit: number;
  offset: number;
};

export type InquiriesFilters = {
  region: string;
  status: string;
  sort: "newest" | "most_followed";
  q: string;
};

export const INQUIRIES_PAGE_SIZE = 20;

export function inquiriesQueryKey(filters: InquiriesFilters) {
  return ["inquiries", filters] as const;
}

export function fetchInquiriesPage(
  filters: InquiriesFilters,
  offset: number,
  fetcher: Fetcher = apiFetch,
) {
  const params = new URLSearchParams();
  if (filters.region) params.set("region", filters.region);
  if (filters.status) params.set("status", filters.status);
  params.set("sort", filters.sort);
  if (filters.q) params.set("q", filters.q);
  params.set("limit", String(INQUIRIES_PAGE_SIZE));
  params.set("offset", String(offset));
  return fetcher<InquiriesPage>(`/api/v1/inquiries?${params.toString()}`);
}
