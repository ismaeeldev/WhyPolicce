import { Check, Minus } from "lucide-react";
import Link from "next/link";

type Cell = string | boolean;
type Row = { feature: string; free: Cell; full: Cell; attorney: Cell };

/**
 * Every value here is backed by the product's real rules: post length and file
 * limits are set per inquiry (backend _TIER_LIMITS / _FREE_TIER_CHAR_LIMIT), not
 * per account type, so the attorney column reads "Per post"; the "Your account"
 * features work for any signed-in user; attorney tools are role-gated.
 */
const GROUPS: { group: string; rows: Row[] }[] = [
  {
    group: "Posting",
    rows: [
      { feature: "Post length", free: "250 chars", full: "Unlimited", attorney: "Per post" },
      { feature: "Files per post", free: "1", full: "Up to 5", attorney: "Per post" },
      { feature: "Total file size", free: "5 MB", full: "50 MB", attorney: "Per post" },
    ],
  },
  {
    group: "Your account",
    rows: [
      { feature: "Anonymous posting", free: true, full: true, attorney: true },
      { feature: "Edit or delete any time", free: true, full: true, attorney: true },
      { feature: "Follow inquiries", free: true, full: true, attorney: true },
    ],
  },
  {
    group: "Attorney tools",
    rows: [
      { feature: "Full case ledger", free: false, full: false, attorney: true },
      { feature: "Consultation requests", free: false, full: false, attorney: true },
      { feature: "Client request tracking", free: false, full: false, attorney: true },
      { feature: "Verified badge", free: false, full: false, attorney: true },
      { feature: "Bar verification", free: false, full: false, attorney: "Required" },
    ],
  },
];

function Value({ value }: { value: Cell }) {
  if (value === true) return <Check className="mx-auto h-4 w-4 text-accent" aria-label="Included" />;
  if (value === false) return <Minus className="mx-auto h-4 w-4 text-text-muted/60" aria-label="Not included" />;
  return <span className="text-text-primary">{value}</span>;
}

export function PricingComparison({ onApplyAttorney }: { onApplyAttorney: () => void }) {
  const btn =
    "mt-2 inline-flex min-h-8 items-center justify-center rounded-md px-2 text-caption font-semibold sm:px-3 transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none";
  const ghost = `${btn} border border-border-strong text-text-primary hover:bg-bg-subtle`;
  const solid = `${btn} bg-accent text-accent-foreground hover:bg-accent-hover`;
  // Full-post column is tinted so the highlighted plan reads as one band top to bottom.
  const tint = "bg-accent/[0.06]";

  return (
    <section aria-labelledby="compare-heading" className="mx-auto mt-16 w-full max-w-[1000px]">
      <h2 id="compare-heading" className="text-center font-display text-h2 text-text-primary">
        Compare plans
      </h2>
      <div className="mt-6 overflow-hidden rounded-2xl border border-border-default bg-bg-elevated shadow-card">
        <table className="w-full table-fixed border-collapse text-left text-caption sm:text-body-sm">
          <colgroup>
            <col className="w-[30%] sm:w-[34%]" />
            <col />
            <col />
            <col />
          </colgroup>
          <thead>
            <tr className="border-b border-border-default align-top">
              <td className="px-3 py-4 sm:px-6" />
              <th scope="col" className="px-1 py-4 text-center font-normal sm:px-3">
                <span className="block font-display text-body-sm max-[360px]:text-[13px] text-text-primary sm:text-h3">Free</span>
                <span className="mt-0.5 block text-text-muted">$0</span>
                <Link href="/inquiries/new" className={ghost}>
                  Post
                </Link>
              </th>
              <th scope="col" className={`px-1 py-4 text-center font-normal sm:px-3 ${tint}`}>
                <span className="block font-display text-body-sm max-[360px]:text-[13px] text-text-primary sm:text-h3">
                  <span className="sm:hidden">Full</span>
                  <span className="hidden sm:inline">Full post</span>
                </span>
                <span className="mt-0.5 block text-text-muted">
                  $2.99<span className="hidden sm:inline"> per post</span>
                </span>
                <Link href="/inquiries/new" className={solid}>
                  Start
                </Link>
              </th>
              <th scope="col" className="px-1 py-4 text-center font-normal sm:px-3">
                <span className="block font-display text-body-sm max-[360px]:text-[13px] text-text-primary sm:text-h3">
                  <span className="sm:hidden">Attorney</span>
                  <span className="hidden sm:inline">Verified attorney</span>
                </span>
                <span className="mt-0.5 block text-text-muted">
                  $149<span className="hidden sm:inline"> per month</span>
                  <span className="sm:hidden">/mo</span>
                </span>
                <button type="button" onClick={onApplyAttorney} className={ghost}>
                  Apply
                </button>
              </th>
            </tr>
          </thead>
          {GROUPS.map((section) => (
            <tbody key={section.group}>
              <tr className="border-t border-border-default bg-bg-subtle/70">
                <th
                  colSpan={4}
                  scope="colgroup"
                  className="px-3 py-2 text-left font-mono text-[11px] font-medium uppercase tracking-wider text-text-muted sm:px-6"
                >
                  {section.group}
                </th>
              </tr>
              {section.rows.map((row) => (
                <tr key={row.feature} className="border-t border-border-default transition-colors hover:bg-bg-subtle/40">
                  <th scope="row" className="break-words px-3 py-3 font-normal text-text-primary max-[360px]:px-2 sm:px-6">
                    {row.feature}
                  </th>
                  <td className="px-1 py-3 text-center sm:px-3">
                    <Value value={row.free} />
                  </td>
                  <td className={`px-1 py-3 text-center sm:px-3 ${tint}`}>
                    <Value value={row.full} />
                  </td>
                  <td className="px-1 py-3 text-center sm:px-3">
                    <Value value={row.attorney} />
                  </td>
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
      <p className="mt-3 text-center text-caption text-text-muted">
        Post length and file limits apply to each inquiry, whatever type of account posts it.
      </p>
    </section>
  );
}
