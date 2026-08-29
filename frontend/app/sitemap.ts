import type { MetadataRoute } from "next";

/**
 * Public-routes-only sitemap — AgentGuide/02_ApplicationFlow.md §5.3.
 * Protected routes are excluded. /login and /signup are also intentionally
 * excluded per standard SEO practice (auth pages aren't indexing targets),
 * and /dev/* is internal QA tooling, never public.
 */
const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://whypolice.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const routes = ["/", "/about", "/pricing", "/privacy", "/terms"];
  return routes.map((route) => ({
    url: `${BASE_URL}${route}`,
    lastModified: new Date(),
    changeFrequency: route === "/" ? "weekly" : "monthly",
    priority: route === "/" ? 1 : 0.6,
  }));
}
