"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";

type Item = { q: string; a: string };

const FAQ: { tab: string; items: Item[] }[] = [
  {
    tab: "Plans and usage",
    items: [
      {
        q: "Is posting really free?",
        a: "Yes. Anyone can post an inquiry of up to 250 characters with one attachment, for free and with no time limit.",
      },
      {
        q: "What is the difference between Free and Full post?",
        a: "A free post is limited to 250 characters and one file of up to 5 MB. A Full post removes the character limit and allows up to 5 files, 50 MB in total, for that one inquiry.",
      },
      {
        q: "When would I pay the $2.99?",
        a: "Only when a post needs more than 250 characters or more than one file. You can pay when you publish, or upgrade an existing post later from its page or from this pricing page.",
      },
    ],
  },
  {
    tab: "Billing and payments",
    items: [
      {
        q: "Is the $2.99 a subscription?",
        a: "No. It is a one-time fee for a single inquiry and never renews.",
      },
      {
        q: "How much is the attorney subscription?",
        a: "$149 per month, charged once your application has been approved.",
      },
      {
        q: "How is billing handled?",
        a: "Payments are processed by Stripe. WhyPolice never sees or stores your card details.",
      },
    ],
  },
  {
    tab: "Managing your account",
    items: [
      {
        q: "Can I edit or delete my inquiry?",
        a: "Yes, at any time and with no time limit, on both Free and Full posts.",
      },
      {
        q: "Can I post without my name showing?",
        a: "Yes. Tick the anonymous option when you post. Your identity is never published on any inquiry, anonymous or not.",
      },
      {
        q: "Who can subscribe as an attorney?",
        a: "Licensed attorneys. You apply with your bar number and jurisdiction, and an administrator reviews the application by hand. You can follow its status on your account page.",
      },
    ],
  },
];

/**
 * Accordion row. Height animates via a CSS grid-template-rows transition
 * (0fr -> 1fr), which animates to the content's real height with no JS
 * measuring — the usual cause of jumpy accordions (display toggles, or
 * animating max-height/height: auto). The collapsed panel is `inert` so its
 * links/text can't be tabbed to while hidden.
 */
function AccordionItem({ item }: { item: Item }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="border-b border-border-default last:border-0">
      <h3>
        <button
          type="button"
          id={`${id}-button`}
          aria-expanded={open}
          aria-controls={`${id}-panel`}
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-body font-medium text-text-primary outline-none transition-colors hover:bg-bg-subtle/60 focus-visible:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent"
        >
          <span>{item.q}</span>
          <ChevronDown
            aria-hidden="true"
            className={`h-4 w-4 shrink-0 text-text-muted transition-transform duration-300 ease-out motion-reduce:transition-none ${
              open ? "rotate-180" : ""
            }`}
          />
        </button>
      </h3>
      <div
        id={`${id}-panel`}
        role="region"
        aria-labelledby={`${id}-button`}
        inert={!open}
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out motion-reduce:transition-none ${
          open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="min-h-0 overflow-hidden">
          <p className="px-5 pb-5 text-body-sm leading-relaxed text-text-secondary">{item.a}</p>
        </div>
      </div>
    </div>
  );
}

export function PricingFaq() {
  const [active, setActive] = useState(0);
  return (
    <section aria-labelledby="faq-heading" className="mx-auto mt-20 w-full max-w-[760px]">
      <h2 id="faq-heading" className="text-center font-display text-h2 text-text-primary">
        Frequently asked questions
      </h2>

      <div
        role="tablist"
        aria-label="FAQ topics"
        className="mt-6 flex flex-wrap justify-center gap-1 border-b border-border-default"
      >
        {FAQ.map((group, i) => (
          <button
            key={group.tab}
            type="button"
            role="tab"
            id={`faq-tab-${i}`}
            aria-selected={active === i}
            aria-controls={`faq-panel-${i}`}
            onClick={() => setActive(i)}
            className={`-mb-px border-b-2 px-4 py-2.5 text-body-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-accent ${
              active === i
                ? "border-accent text-text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {group.tab}
          </button>
        ))}
      </div>

      {/* All panels share one grid cell so the section is always as tall as the
          tallest panel — switching tabs never resizes the page below it. */}
      <div className="mt-6 grid">
        {FAQ.map((group, i) => (
          <div
            key={group.tab}
            id={`faq-panel-${i}`}
            role="tabpanel"
            aria-labelledby={`faq-tab-${i}`}
            inert={active !== i}
            className={`col-start-1 row-start-1 self-start overflow-hidden rounded-xl border border-border-default bg-bg-elevated transition-opacity duration-200 motion-reduce:transition-none ${
              active === i ? "opacity-100" : "pointer-events-none opacity-0"
            }`}
          >
            {group.items.map((item) => (
              <AccordionItem key={item.q} item={item} />
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
