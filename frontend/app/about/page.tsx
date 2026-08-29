import type { Metadata } from "next";

import { ScrollReveal } from "@/components/marketing/ScrollReveal";

export const metadata: Metadata = {
  title: "About — WhyPolice",
  description:
    "Why we built a search product that streams answers in real time, keeps accounts spam-free, and never turns your questions into a product.",
  openGraph: {
    title: "About — WhyPolice",
    description:
      "Why we built a search product that streams answers in real time, keeps accounts spam-free, and never turns your questions into a product.",
    type: "website",
  },
};

const PARAGRAPHS = [
  <>
    Somewhere along the way, search stopped being about answers. It
    became ten blue links, three ads above the fold, and a page you
    scroll through hoping something useful is buried in it. We wanted
    the opposite: ask a real question, watch the answer arrive as it&apos;s
    formed, and move on with your day.
  </>,
  <>
    That&apos;s the whole idea behind WhyPolice. You type a question the way
    you&apos;d ask a person. The answer streams back in real time — no
    spinner, no waiting for a page to finish loading, just the response
    building itself in front of you.
  </>,
  <>
    We ask you to sign in before searching, and we know that&apos;s a small
    bit of friction. It&apos;s there for one reason: to keep the platform
    free of bots and spam, not to build a profile on you. Your searches
    stay yours — we don&apos;t sell them, share them, or hand them to anyone
    else.
  </>,
  <>
    Every search you run is saved to your own history so you can come
    back to it, export it, or clear it whenever you want. That&apos;s the
    extent of what we keep, and it&apos;s entirely under your control.
  </>,
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-[680px] px-6 py-20 sm:py-28">
      <ScrollReveal>
        <h1 className="font-display text-display-lg leading-[1.1] mb-8">
          We got tired of searching for the search results.
        </h1>
      </ScrollReveal>

      <ScrollReveal className="space-y-6 text-body-lg text-text-secondary leading-relaxed">
        {PARAGRAPHS.map((paragraph, i) => (
          <p key={i}>{paragraph}</p>
        ))}
        <p className="text-text-primary font-medium">
          We&apos;re building the search we wanted to use ourselves — calm, fast,
          and honest about what it does with your questions.
        </p>
      </ScrollReveal>
    </div>
  );
}
