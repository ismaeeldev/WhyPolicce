import type { Metadata } from "next";
import { Sparkles } from "lucide-react";

import { HeroContent } from "@/components/marketing/HeroContent";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";

export const metadata: Metadata = {
  title: "WhyPolice — Public safety intelligence, live.",
  description:
    "Ask about police reports, case updates, and public safety data — and watch a clear, sourced answer stream in as it's written. Sign up free.",
  openGraph: {
    title: "WhyPolice — Public safety intelligence, live.",
    description:
      "Ask about police reports, case updates, and public safety data — and watch a clear, sourced answer stream in as it's written.",
    type: "website",
  },
};

const STEPS = [
  {
    n: "01",
    title: "Ask, plainly",
    body: "Type a real question about a case, report, or local safety policy — no keyword-stuffing required.",
  },
  {
    n: "02",
    title: "Watch it think",
    body: "The answer streams in live, token by token, so you're never staring at a blank screen.",
  },
  {
    n: "03",
    title: "Keep what matters",
    body: "Every search is saved to your history, exportable any time, gone the moment you clear it.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col flex-1">
      {/* Hero */}
      <section className="relative flex flex-1 items-center justify-center overflow-hidden py-24 sm:py-32 px-6">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-24 right-[8%] h-[420px] w-[420px] rounded-full opacity-[0.14] blur-3xl animate-wp-drift"
          style={{
            background:
              "radial-gradient(circle, var(--wp-accent-bright) 0%, transparent 70%)",
          }}
        />
        <div className="relative mx-auto flex w-full max-w-[900px] flex-col items-center text-center">
          {/* Plain static markup, not a client component — this is the page's
              Largest Contentful Paint element, it must paint with the initial
              HTML, never gated behind client-side JS/animation. See
              components/marketing/HeroContent.tsx for why. */}
          <h1 className="font-display text-display-lg sm:text-display-xl leading-[1.05] text-text-primary">
            Public safety intelligence.
            <br />
            Answered live.
          </h1>
          <HeroContent />
        </div>
      </section>

      {/* How it works — numbered flow, deliberately not a 3-icon grid */}
      <section className="border-t border-border-default py-20 sm:py-28 px-6">
        <div className="mx-auto max-w-[1000px]">
          <ScrollReveal className="grid gap-10 sm:grid-cols-3 sm:gap-6">
            {STEPS.map((step, i) => (
              <div key={step.n} className="relative">
                {i < STEPS.length - 1 && (
                  <div className="hidden sm:block absolute top-5 left-[calc(100%-1rem)] w-[calc(100%-1.5rem)] h-px bg-border-default" />
                )}
                <span className="font-display text-2xl text-accent">{step.n}</span>
                <h2 className="text-h3 font-semibold mt-3 mb-1.5">{step.title}</h2>
                <p className="text-body-sm text-text-secondary">{step.body}</p>
              </div>
            ))}
          </ScrollReveal>
        </div>
      </section>

      {/* Product principle — a single editorial statement, not another grid */}
      <section className="border-t border-border-default py-20 sm:py-28 px-6 bg-bg-subtle">
        <ScrollReveal className="mx-auto max-w-[720px] text-center">
          <Sparkles className="h-6 w-6 text-accent mx-auto mb-6" strokeWidth={1.5} />
          <p className="font-display text-2xl sm:text-3xl leading-snug text-text-primary">
            We built WhyPolice on one belief: public safety information
            shouldn&apos;t take a dozen tabs and a records request to
            understand. Ask plainly, get a clear answer.
          </p>
        </ScrollReveal>
      </section>

      {/* Privacy note — plain text, no card/border/icon-badge. why.com never
          wraps a single paragraph in decorative chrome; the restraint IS
          the design. Kept as its own section purely for vertical rhythm. */}
      <section className="border-t border-border-default py-16 sm:py-20 px-6">
        <ScrollReveal className="mx-auto max-w-[620px] text-center">
          <h2 className="text-h3 font-semibold mb-2">Your searches are yours</h2>
          <p className="text-body-sm text-text-secondary">
            An account keeps bots and spam off the platform — it doesn&apos;t
            turn your questions into a product. Nothing you search is sold,
            shared, or handed to anyone else.
          </p>
        </ScrollReveal>
      </section>
    </div>
  );
}
