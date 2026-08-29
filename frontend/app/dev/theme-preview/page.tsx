"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Internal QA page — NOT linked in nav. Renders every color swatch, type
 * scale, button variant, and skeleton primitive from AgentGuide/01_ThemeGuideline.md
 * side by side, plus a live contrast readout per §11's Agent Usage Notes.
 */

const SWATCHES: { name: string; varName: string }[] = [
  { name: "bg", varName: "--wp-bg" },
  { name: "bg-elevated", varName: "--wp-bg-elevated" },
  { name: "bg-subtle", varName: "--wp-bg-subtle" },
  { name: "border", varName: "--wp-border" },
  { name: "border-strong", varName: "--wp-border-strong" },
  { name: "text-primary", varName: "--wp-text-primary" },
  { name: "text-secondary", varName: "--wp-text-secondary" },
  { name: "text-muted", varName: "--wp-text-muted" },
  { name: "accent", varName: "--wp-accent" },
  { name: "accent-hover", varName: "--wp-accent-hover" },
  { name: "accent-bright", varName: "--wp-accent-bright" },
  { name: "accent-subtle", varName: "--wp-accent-subtle" },
  { name: "success", varName: "--wp-success" },
  { name: "warning", varName: "--wp-warning" },
  { name: "warning-subtle", varName: "--wp-warning-subtle" },
  { name: "danger", varName: "--wp-danger" },
  { name: "danger-subtle", varName: "--wp-danger-subtle" },
];

function relLum(hex: string) {
  const c = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(c.slice(i, i + 2), 16) / 255);
  const lin = (v: number) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function contrastRatio(hexA: string, hexB: string) {
  const la = relLum(hexA);
  const lb = relLum(hexB);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

function readCssVar(name: string): string {
  if (typeof window === "undefined") return "#000000";
  const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return val || "#000000";
}

function ContrastRow({ label, fgVar, bgVar }: { label: string; fgVar: string; bgVar: string }) {
  const [ratio, setRatio] = useState<number | null>(null);

  useEffect(() => {
    // Reading a resolved CSS custom property requires the DOM to have painted —
    // this is exactly the "subscribe to an external system" case an effect is for,
    // not derivable from props/state alone. eslint-disable is intentional here.
    const fg = readCssVar(fgVar);
    const bg = readCssVar(bgVar);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRatio(contrastRatio(fg, bg));
  }, [fgVar, bgVar]);

  const pass = ratio !== null && ratio >= 4.5;
  return (
    <div className="flex items-center justify-between border-b border-border-default py-2 text-sm">
      <span>{label}</span>
      <span className={pass ? "text-success font-medium" : "text-danger font-medium"}>
        {ratio ? ratio.toFixed(2) : "…"}:1 — {pass ? "PASS AA" : "check"}
      </span>
    </div>
  );
}

export default function ThemePreviewPage() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    // Standard next-themes hydration-mismatch guard (server can't know the
    // resolved theme) — mount-flip pattern is unavoidable here, disable is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-12 space-y-16">
      <header className="flex items-center justify-between">
        <h1 className="font-display text-3xl">Theme Preview (internal QA)</h1>
        {mounted && (
          <button
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            className="rounded-sm border border-border-strong px-3 py-1.5 text-sm hover:bg-bg-subtle transition-colors"
          >
            Toggle theme (current: {theme})
          </button>
        )}
      </header>

      {/* Color swatches */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Color tokens</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {SWATCHES.map((s) => (
            <div key={s.name} className="text-center">
              <div
                className="h-16 rounded-md border border-border-default mb-1.5"
                style={{ background: `var(${s.varName})` }}
              />
              <span className="text-caption text-text-secondary">{s.name}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Type scale */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Type scale</h2>
        <div className="space-y-3">
          <p className="font-display text-display-xl">Display XL</p>
          <p className="font-display text-display-lg">Display LG</p>
          <h1 className="text-h1 font-semibold">H1 Page title</h1>
          <h2 className="text-h2 font-semibold">H2 Section title</h2>
          <h3 className="text-h3 font-semibold">H3 Subsection</h3>
          <p className="text-body-lg">Body LG — lead paragraph text</p>
          <p className="text-body">Body — default paragraph text</p>
          <p className="text-body-sm text-text-secondary">Body SM — secondary text</p>
          <p className="text-caption text-text-muted uppercase tracking-wide">Caption / meta</p>
        </div>
      </section>

      {/* Button variants — matching AgentGuide/01_ThemeGuideline.md §4.2 exactly */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Buttons</h2>
        <div className="flex flex-wrap items-center gap-3">
          <button className="h-11 px-5 rounded-sm bg-accent text-accent-foreground text-base font-medium transition-all hover:bg-accent-hover hover:scale-[1.02] focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none">
            Primary
          </button>
          <button className="h-11 px-5 rounded-sm border border-border-strong text-text-primary text-base font-medium transition-colors hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none">
            Secondary
          </button>
          <button className="h-11 px-5 rounded-sm text-text-secondary text-base font-medium transition-colors hover:bg-bg-subtle hover:text-text-primary focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none">
            Ghost
          </button>
          <button className="h-11 px-5 rounded-sm bg-danger text-danger-foreground text-base font-medium transition-colors hover:opacity-90 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none">
            Destructive
          </button>
          <button
            disabled
            className="h-11 px-5 rounded-sm bg-bg-subtle text-text-muted text-base font-medium cursor-not-allowed"
          >
            Disabled
          </button>
        </div>
      </section>

      {/* Skeleton example next to a loaded equivalent */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Skeleton vs. loaded (§4.9)</h2>
        <div className="grid grid-cols-2 gap-6 max-w-md">
          <div className="rounded-md border border-border-default bg-bg-elevated shadow-card p-4 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-1/2" />
          </div>
          <div className="rounded-md border border-border-default bg-bg-elevated shadow-card p-4 space-y-2">
            <p className="text-sm">This is the loaded content that the</p>
            <p className="text-sm">skeleton on the left mirrors exactly —</p>
            <p className="text-sm">same height, spacing, radius.</p>
          </div>
        </div>
      </section>

      {/* Live contrast readout */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Live contrast readout (§1.4 verification)</h2>
        <div className="max-w-md">
          <ContrastRow label="text-muted on bg" fgVar="--wp-text-muted" bgVar="--wp-bg" />
          <ContrastRow label="text-secondary on bg" fgVar="--wp-text-secondary" bgVar="--wp-bg" />
          <ContrastRow label="accent (text) on bg" fgVar="--wp-accent" bgVar="--wp-bg" />
          <ContrastRow label="warning on bg" fgVar="--wp-warning" bgVar="--wp-bg" />
          <ContrastRow label="success on bg" fgVar="--wp-success" bgVar="--wp-bg" />
          <ContrastRow label="danger on bg" fgVar="--wp-danger" bgVar="--wp-bg" />
        </div>
      </section>
    </div>
  );
}
