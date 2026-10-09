import type { Metadata } from "next";

import { ThreadPageClient } from "@/components/inquiries/ThreadPageClient";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://whypolice.com";

type Props = { params: Promise<{ id: string }> };

/**
 * Each inquiry gets its own title/description/preview so a shared link is
 * meaningful instead of the generic site title. Reads the same public endpoint
 * any visitor can; an unpaid draft or missing inquiry 404s there and is kept
 * out of search indexes.
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const canonical = `${SITE_URL}/inquiries/${id}`;
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/inquiries/${encodeURIComponent(id)}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return { title: "Inquiry not found — WhyPolice", robots: { index: false, follow: false } };
    const inquiry: { title: string; description: string; city: string; state: string } = await res.json();
    const summary = inquiry.description.replace(/\s+/g, " ").trim();
    const description = `${inquiry.city}, ${inquiry.state} — ${summary.length > 150 ? `${summary.slice(0, 149)}…` : summary}`;
    return {
      title: `${inquiry.title} — WhyPolice`,
      description,
      alternates: { canonical },
      openGraph: { title: inquiry.title, description, type: "article", url: canonical },
    };
  } catch {
    return { title: "Inquiry — WhyPolice" };
  }
}

export default function InquiryThreadPage() {
  return <ThreadPageClient />;
}
