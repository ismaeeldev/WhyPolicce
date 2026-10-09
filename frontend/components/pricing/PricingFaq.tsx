import { ChevronDown } from "lucide-react";

const FAQ: { q: string; a: string }[] = [
  {
    q: "Is posting really free?",
    a: "Yes. Anyone can post an inquiry of up to 250 characters with one attachment, for free and with no time limit. You can edit or delete it whenever you like.",
  },
  {
    q: "When would I pay the $2.99?",
    a: "Only if a post needs more than 250 characters or more than one file. It is a one-time fee for that single inquiry, not a subscription, and you can upgrade from the post itself at any time.",
  },
  {
    q: "Can I post without my name showing?",
    a: "Yes. Tick the anonymous option when you post. Your identity is never published on any inquiry, anonymous or not.",
  },
  {
    q: "Who can subscribe as an attorney?",
    a: "Licensed attorneys. You apply with your bar number and jurisdiction, and an administrator reviews the application by hand. The $149/month subscription starts once you are approved.",
  },
  {
    q: "How is billing handled?",
    a: "Payments are processed by Stripe. WhyPolice never sees or stores your card details.",
  },
];

export function PricingFaq() {
  return (
    <section aria-labelledby="faq-heading" className="mx-auto mt-20 w-full max-w-[720px]">
      <h2 id="faq-heading" className="font-display text-h2 text-text-primary text-center">
        Frequently asked questions
      </h2>
      <div className="mt-6 divide-y divide-border-default rounded-xl border border-border-default bg-bg-elevated">
        {FAQ.map((item) => (
          <details key={item.q} className="group px-5 py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-body font-medium text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-accent [&::-webkit-details-marker]:hidden">
              {item.q}
              <ChevronDown className="h-4 w-4 shrink-0 text-text-muted transition-transform group-open:rotate-180" />
            </summary>
            <p className="mt-3 text-body-sm leading-relaxed text-text-secondary">{item.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
