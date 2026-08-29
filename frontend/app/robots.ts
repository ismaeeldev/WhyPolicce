import type { MetadataRoute } from "next";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://whypolice.com";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/search", "/history", "/account", "/upgrade", "/dev/"],
    },
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
