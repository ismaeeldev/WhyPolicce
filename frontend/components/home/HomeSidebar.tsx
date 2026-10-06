"use client";

import { CheckCircle2, Globe, MapPin, Shield, Star } from "lucide-react";
import Link from "next/link";

import { useInquiryStats } from "@/hooks/useInquiries";
import { attorneyDisplayName, attorneyInitials, useVerifiedAttorneys } from "@/hooks/useVerifiedAttorneys";

export function HomeSidebar() {
  const { data: stats } = useInquiryStats();
  const { data: attorneys, isLoading } = useVerifiedAttorneys(1);
  const spotlight = attorneys?.[0];

  const total = stats?.totalRecords ?? 0;
  const pct = (n: number | undefined) => (total > 0 && n !== undefined ? Math.round((n / total) * 100) : 0);
  const rows = [
    { label: "Community Trace", value: stats?.communityTrace, bar: "bg-success", text: "text-success" },
    { label: "Awaiting Police Statement", value: stats?.awaitingPoliceStatement, bar: "bg-info", text: "text-info" },
    { label: "Posted in last 30 days", value: stats?.last30Days, bar: "bg-accent", text: "text-text-primary" },
  ];

  return (
    <aside className="flex flex-col gap-6">
      {/* Widget 1: Attorney Spotlight — real, admin-approved attorney */}
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

        {isLoading && <div className="h-[72px] rounded-lg bg-bg-subtle/70 animate-pulse mb-3" />}

        {!isLoading && !spotlight && (
          <p className="py-4 text-center text-caption text-text-muted">
            No verified attorneys listed yet.
          </p>
        )}

        {spotlight && (
          <>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-subtle/70 border border-border-default/40 mb-3">
              <div className="h-11 w-11 shrink-0 rounded-full bg-accent/20 border border-accent/40 text-accent font-mono font-bold flex items-center justify-center text-body">
                {attorneyInitials(spotlight)}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-body-sm font-semibold text-text-primary truncate">
                    {attorneyDisplayName(spotlight)}
                  </span>
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-accent" aria-label="Verified" />
                </div>
                <div className="text-[11px] text-text-muted">Verified attorney</div>
              </div>
            </div>

            <div className="space-y-2 text-[11px] text-text-secondary mb-4 px-1">
              {spotlight.barJurisdiction && (
                <div className="flex items-center gap-2">
                  <MapPin className="h-3 w-3 text-text-muted" />
                  <span className="font-mono text-text-primary">Licensed in {spotlight.barJurisdiction}</span>
                </div>
              )}
              {spotlight.firmWebsite && (
                <div className="flex items-center gap-2 min-w-0">
                  <Globe className="h-3 w-3 shrink-0 text-text-muted" />
                  <a
                    href={spotlight.firmWebsite}
                    target="_blank"
                    rel="noopener noreferrer nofollow"
                    className="font-mono text-text-muted hover:text-accent truncate transition-colors"
                  >
                    {spotlight.firmWebsite.replace(/^https?:\/\/(www\.)?/, "")}
                  </a>
                </div>
              )}
            </div>
          </>
        )}

        <Link
          href="/pricing"
          className="inline-flex items-center justify-center w-full rounded-lg border border-accent/40 bg-accent/10 px-4 py-2.5 text-caption font-semibold text-accent hover:bg-accent hover:text-accent-foreground transition-all focus-visible:ring-2 focus-visible:ring-accent outline-none shadow-sm"
        >
          Explore Legal Network &rarr;
        </Link>
      </div>

      {/* Widget 2: Platform Transparency — live breakdown of public records */}
      <div className="rounded-xl border border-border-default/80 bg-bg-elevated p-5 shadow-card">
        <div className="flex items-center gap-2 font-semibold text-body-sm text-text-primary mb-3">
          <Shield className="h-4 w-4 text-accent" />
          <span>Platform Transparency</span>
        </div>
        <div className="space-y-3.5 text-caption">
          {rows.map((row) => (
            <div key={row.label}>
              <div className="flex justify-between text-text-secondary mb-1.5">
                <span>{row.label}</span>
                <span className={`font-mono font-bold ${row.text}`}>
                  {row.value === undefined ? "—" : row.value.toLocaleString()}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-bg-subtle overflow-hidden">
                <div className={`h-full ${row.bar} rounded-full`} style={{ width: `${pct(row.value)}%` }} />
              </div>
            </div>
          ))}
          <p className="text-[10px] font-mono text-text-muted pt-1">
            Share of {total.toLocaleString()} public records across {stats?.totalStates ?? "—"} states.
          </p>
        </div>
      </div>
    </aside>
  );
}
