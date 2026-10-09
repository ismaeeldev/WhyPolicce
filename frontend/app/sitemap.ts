import type { MetadataRoute } from "next";

/**
 * Public-routes-only sitemap — AgentGuide/02_ApplicationFlow.md §5.3.
 * Protected routes are excluded. /login and /signup are also intentionally
 * excluded per standard SEO practice (auth pages aren't indexing targets),
 * and /dev/* is internal QA tooling, never public. Public inquiry pages (the
 * site's actual content) are included, newest first, refreshed hourly.
 */
const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://whypolice.com";
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const routes = ["/", "/about", "/pricing", "/privacy", "/terms"];
  const staticEntries: MetadataRoute.Sitemap = routes.map((route) => ({
    url: `${BASE_URL}${route}`,
    changeFrequency: route === "/" ? "weekly" : "monthly",
    priority: route === "/" ? 1 : 0.6,
  }));

  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/inquiries?limit=100&sort=newest`, { next: { revalidate } });
    if (!res.ok) return staticEntries;
    const { items } = (await res.json()) as { items: { id: string; updatedAt: string }[] };
    return [
      ...staticEntries,
      ...items.map((item) => ({
        url: `${BASE_URL}/inquiries/${item.id}`,
        lastModified: new Date(item.updatedAt),
        changeFrequency: "weekly" as const,
        priority: 0.5,
      })),
    ];
  } catch {
    return staticEntries;
  }
}
