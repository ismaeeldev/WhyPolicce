import type { Metadata } from "next";
import { Sparkles } from "lucide-react";

import { HeroContent } from "@/components/marketing/HeroContent";
import { ScrollReveal } from "@/components/marketing/ScrollReveal";
import { TypedHeadline } from "@/components/marketing/TypedHeadline";

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
          {/* Revision 3 Step 7 (plan.md): why.com's real headline is a live,
              rotating, character-typed question (verified via live DOM
              inspection — a genuine typewriter effect with a blinking
              caret), not a static tagline. TypedHeadline renders the FIRST
              question as plain static text on the server (LCP-safe, per
              the original finding this replaces: gating the H1 behind
              client JS cost ~550ms of real LCP) — the typing/deleting
              animation only begins after hydration, never blocking
              initial paint. */}
          <TypedHeadline />
          <HeroContent />
        </div>
      </section>

      {/* How it works — numbered flow, deliberately not a 3-icon grid.
          Connecting line now animates its own width in alongside the
          stagger (was a static full-width line) so the "flow" reads as
          something happening, not just three cards sitting next to a
          decorative rule. */}
      <section className="relative border-t border-border-default py-20 sm:py-28 px-6 overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-[0.4]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, var(--wp-border) 1px, transparent 0)",
            backgroundSize: "28px 28px",
            maskImage: "radial-gradient(ellipse 60% 100% at 50% 0%, black, transparent)",
          }}
        />
        <div className="relative mx-auto max-w-[1000px]">
          <ScrollReveal className="grid gap-10 sm:grid-cols-3 sm:gap-6">
            {STEPS.map((step, i) => (
              <div key={step.n} className="group relative">
                {i < STEPS.length - 1 && (
                  <div className="hidden sm:block absolute top-5 left-[calc(100%-1rem)] w-[calc(100%-1.5rem)] h-px overflow-hidden bg-border-default">
                    <div className="wp-line-draw h-full w-full origin-left bg-accent/40" />
                  </div>
                )}
                <span className="font-display text-2xl text-accent transition-transform duration-300 group-hover:scale-110 inline-block">
                  {step.n}
                </span>
                <h2 className="text-h3 font-semibold mt-3 mb-1.5">{step.title}</h2>
                <p className="text-body-sm text-text-secondary">{step.body}</p>
              </div>
            ))}
          </ScrollReveal>
        </div>
      </section>

      {/* Product principle — a single editorial statement, not another grid.
          Was a flat bg-subtle rectangle with only a Sparkles icon for
          visual interest; added a soft radial glow + hairline top/bottom
          accent rule so the section reads as a considered "pull quote"
          moment rather than a plain color-block break between sections. */}
      <section className="relative border-t border-border-default py-20 sm:py-28 px-6 bg-bg-subtle overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute left-1/2 top-1/2 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-[0.08] blur-3xl"
          style={{
            background: "radial-gradient(circle, var(--wp-accent-bright) 0%, transparent 70%)",
          }}
        />
        <ScrollReveal className="relative mx-auto max-w-[720px] text-center">
          <span className="mx-auto mb-6 block h-px w-12 bg-accent/50" />
          <Sparkles className="h-6 w-6 text-accent mx-auto mb-6" strokeWidth={1.5} />
          <p className="font-display text-2xl sm:text-3xl leading-snug text-text-primary text-balance">
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
