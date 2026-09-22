import type { Metadata } from "next";

import { ScrollReveal } from "@/components/marketing/ScrollReveal";

export const metadata: Metadata = {
  title: "About — WhyPolice",
  description:
    "WhyPolice is a public forum where anyone can post about a police interaction or local incident, get real replies from their community, and connect with a verified attorney if they need one.",
  openGraph: {
    title: "About — WhyPolice",
    description:
      "WhyPolice is a public forum where anyone can post about a police interaction or local incident, get real replies from their community, and connect with a verified attorney if they need one.",
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
        When something happens with police, or you&apos;re trying to make sense of
        a local incident, there&apos;s rarely one place to ask about it. Police
        department sites, municipal logs, and records requests all take time —
        time you don&apos;t have when you need to know what to do next. We wanted
        somewhere you could post what happened and actually hear back, from
        real people and, when it matters, from a real attorney.
      </>
    ),
  },
  {
    n: "02",
    title: "How it works",
    body: (
      <>
        You post an inquiry — what happened, where, and what kind of situation
        it is — and it&apos;s visible to everyone, no sign-in required just to
        read. Other people can follow it and reply. If your case needs legal
        help, a verified attorney can request a consultation directly on your
        post; you decide whether to accept.
      </>
    ),
  },
  {
    n: "03",
    title: "Why we ask you to sign in to post",
    body: (
      <>
        Reading the forum is open to anyone. Posting, following, and
        commenting need an account — that&apos;s there for one reason: to keep
        the forum free of bots and spam, not to build a profile on you.
      </>
    ),
  },
  {
    n: "04",
    title: "What attorneys can and can't see",
    body: (
      <>
        Attorneys never see your email or contact details — only your public
        post, same as everyone else. A consultation request only ever reaches
        you through your own inquiry page; nothing is shared until you decide
        to respond.
      </>
    ),
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto w-full min-w-0 max-w-[680px] px-5 sm:px-6 py-12 sm:py-20">
      <div className="wp-page-intro">
        <p className="wp-eyebrow mb-4">Our perspective</p>
        <h1 className="font-display text-h1 sm:text-display-lg leading-[1.1] mb-14">
          Nobody should have to figure this out alone.
        </h1>
      </div>

      <ScrollReveal className="flex flex-col gap-10">
        {SECTIONS.map((section) => (
          <div key={section.n} className="flex gap-4 border-t border-border-default pt-7 sm:gap-6">
            <span className="font-display text-xl text-accent shrink-0 pt-0.5">
              {section.n}
            </span>
            <div>
              <h2 className="text-h3 font-semibold text-text-primary mb-1.5">
                {section.title}
              </h2>
              <p className="text-body sm:text-body-lg text-text-secondary leading-relaxed">
                {section.body}
              </p>
            </div>
          </div>
        ))}
      </ScrollReveal>

      <ScrollReveal className="mt-14 border-t border-border-default pt-8">
        <p className="font-display text-xl sm:text-2xl leading-snug text-text-primary text-balance">
          We&apos;re building the forum we wished existed the first time we
          needed it — public, honest, and never harder to use than it has
          to be.
        </p>
      </ScrollReveal>
    </div>
  );
}
