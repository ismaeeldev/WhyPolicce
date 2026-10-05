"use client";

import { CheckCircle2, Globe, Mail, Phone, Shield, ShieldAlert, Star } from "lucide-react";
import Link from "next/link";

export function HomeSidebar({ onSelectPrecinct }: { onSelectPrecinct?: (precinct: string) => void } = {}) {
  return (
    <aside className="flex flex-col gap-6">
      {/* Widget 1: Attorney Spotlight (matching Image 2) */}
      <div className="rounded-xl border border-border-default/80 bg-bg-elevated p-5 shadow-card transition-all hover:border-accent/40 hover:shadow-card-lg">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 font-semibold text-body-sm text-text-primary">
            <Star className="h-4 w-4 text-accent fill-accent" />
            <span>Attorney Spotlight</span>
          </div>
          <Link
            href="/pricing"
            className="text-[11px] font-mono text-text-muted hover:text-accent transition-colors"
          >
            View All &rarr;
          </Link>
        </div>

        <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-subtle/70 border border-border-default/40 mb-3">
          <div className="h-11 w-11 shrink-0 rounded-full bg-accent/20 border border-accent/40 text-accent font-mono font-bold flex items-center justify-center text-body">
            JW
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-body-sm font-semibold text-text-primary">John William</span>
              <CheckCircle2 className="h-3.5 w-3.5 text-accent" />
            </div>
            <div className="text-[11px] text-text-muted">Police Misconduct Lawyer</div>
          </div>
        </div>

        <div className="space-y-2 text-[11px] text-text-secondary mb-4 px-1">
          <div className="flex items-center gap-2">
            <Phone className="h-3 w-3 text-text-muted" />
            <span className="font-mono text-text-primary">(223) 456-7873</span>
          </div>
          <div className="flex items-center gap-2">
            <Mail className="h-3 w-3 text-text-muted" />
            <span className="font-mono text-text-primary">john@whypolice.com</span>
          </div>
          <div className="flex items-center gap-2">
            <Globe className="h-3 w-3 text-text-muted" />
            <span className="font-mono text-text-muted">www.whypolice.com</span>
          </div>
        </div>

        <Link
          href="/pricing"
          className="inline-flex items-center justify-center w-full rounded-lg border border-accent/40 bg-accent/10 px-4 py-2.5 text-caption font-semibold text-accent hover:bg-accent hover:text-accent-foreground transition-all focus-visible:ring-2 focus-visible:ring-accent outline-none shadow-sm"
        >
          Schedule Consultation &rarr;
        </Link>
      </div>

      {/* Widget 2: Platform Transparency Stats */}
      <div className="rounded-xl border border-border-default/80 bg-bg-elevated p-5 shadow-card">
        <div className="flex items-center gap-2 font-semibold text-body-sm text-text-primary mb-3">
          <Shield className="h-4 w-4 text-accent" />
          <span>Platform Transparency</span>
        </div>
        <div className="space-y-3.5 text-caption">
          <div>
            <div className="flex justify-between text-text-secondary mb-1.5">
              <span>Average Inquiry Response</span>
              <span className="font-mono font-bold text-text-primary">24 hrs</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-bg-subtle overflow-hidden">
              <div className="h-full bg-accent rounded-full w-[85%]" />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-text-secondary mb-1.5">
              <span>Verified Evidence Corroboration</span>
              <span className="font-mono font-bold text-success">92%</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-bg-subtle overflow-hidden">
              <div className="h-full bg-success rounded-full w-[92%]" />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-text-secondary mb-1.5">
              <span>Tamper-Proof Encryption</span>
              <span className="font-mono font-bold text-info">100%</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-bg-subtle overflow-hidden">
              <div className="h-full bg-info rounded-full w-[100%]" />
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

