import type { Metadata } from "next";

import { ScrollReveal } from "@/components/marketing/ScrollReveal";

export const metadata: Metadata = {
  title: "About — WhyPolice",
  description:
    "Why we built an AI search product for police reports, municipal logs, and public safety data that streams answers in real time and never turns your questions into a product.",
  openGraph: {
    title: "About — WhyPolice",
    description:
      "Why we built an AI search product for police reports, municipal logs, and public safety data that streams answers in real time and never turns your questions into a product.",
    type: "website",
  },
};

// UI polish pass: four same-weight paragraphs in a row read as one
// monotone wall of text despite having genuinely distinct ideas (the
// problem, the product, the privacy stance, data retention). Restructured
// into labeled sections with the same numbered-marker rhythm already
// established on the homepage's "How it works" flow, so the two pages
// share a visual language instead of About being a plain text dump.
const SECTIONS = [
  {
    n: "01",
    title: "The problem",
    body: (
      <>
        Public safety information is scattered across police department
        sites, municipal logs, and records requests that take days to
        answer a question you needed today. We wanted the opposite: ask a
        real question about a case, a curfew, or a local incident, and
        watch the answer arrive as it&apos;s formed.
      </>
    ),
  },
  {
    n: "02",
    title: "How it works",
    body: (
      <>
        You type a question the way you&apos;d ask a person. The answer
        streams back in real time — no spinner, no waiting for a page to
        finish loading, just the response building itself in front of
        you. When something needs a live, official record rather than a
        general answer, we say so plainly and point you to the right
        source instead of guessing.
      </>
    ),
  },
  {
    n: "03",
    title: "Why we ask you to sign in",
    body: (
      <>
        We know that&apos;s a small bit of friction. It&apos;s there for one
        reason: to keep the platform free of bots and spam, not to build
        a profile on you. Your searches stay yours — we don&apos;t sell
        them, share them, or hand them to anyone else.
      </>
    ),
  },
  {
    n: "04",
    title: "What we keep",
    body: (
      <>
        Every search you run is saved to your own history so you can come
        back to it, export it, or clear it whenever you want. That&apos;s
        the extent of what we keep, and it&apos;s entirely under your
        control.
      </>
    ),
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-[680px] px-6 py-20 sm:py-28">
      <ScrollReveal>
        <h1 className="font-display text-display-lg leading-[1.1] mb-14">
          Public safety information shouldn&apos;t take a records request.
        </h1>
      </ScrollReveal>

      <ScrollReveal className="flex flex-col gap-10">
        {SECTIONS.map((section) => (
          <div key={section.n} className="flex gap-5">
            <span className="font-display text-xl text-accent shrink-0 pt-0.5">
              {section.n}
            </span>
            <div>
              <h2 className="text-h3 font-semibold text-text-primary mb-1.5">
                {section.title}
              </h2>
              <p className="text-body-lg text-text-secondary leading-relaxed">
                {section.body}
              </p>
            </div>
          </div>
        ))}
      </ScrollReveal>

      <ScrollReveal className="mt-14 border-t border-border-default pt-8">
        <p className="font-display text-xl sm:text-2xl leading-snug text-text-primary text-balance">
          We&apos;re building the search we wanted to use ourselves — calm,
          fast, and honest about what it does with your questions.
        </p>
      </ScrollReveal>
    </div>
  );
}
