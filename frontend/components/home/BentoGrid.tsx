"use client";

import { Activity, CheckCircle2, ChevronDown, ChevronRight, Database, Eye, Globe, Lock, MapPin, Navigation, Search, Shield, Users } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

export function BentoGrid({ onSelectPrecinct }: { onSelectPrecinct?: (precinct: string) => void }) {
  const [toggles, setToggles] = useState({
    sanitizeHistory: true,
    securityToggles: false,
    communityAddress: true,
    groupSecurity: false,
    dataRedaction: true,
  });

  const [precinctQuery, setPrecinctQuery] = useState("");

  const handleToggle = (key: keyof typeof toggles) => {
    setToggles((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const popularPrecincts = [
    { label: "NYC · 104th", state: "NY" },
    { label: "Chicago · 012", state: "IL" },
    { label: "Austin · 045", state: "TX" },
  ];

  return (
    <section className="w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-5">
        {/* Tile 1: Jurisdiction Activity Radar */}
        <div className="group relative flex flex-col justify-between overflow-hidden rounded-xl border border-border-default/80 bg-bg-elevated p-5 shadow-card transition-all duration-300 hover:border-accent/50 hover:shadow-card-lg">
          <div>
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 text-accent font-semibold text-body-sm">
                <Activity className="h-4 w-4" />
                <span>Jurisdiction Activity Radar</span>
              </div>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-0.5 text-[11px] font-mono text-text-muted hover:text-accent transition-colors"
              >
                <span>View All</span>
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>

            <div className="flex justify-end mb-2">
              <div className="inline-flex items-center gap-1 rounded bg-bg-subtle px-2 py-0.5 text-[10px] font-mono text-text-muted border border-border-default/50">
                <span>Last 30 Days</span>
                <ChevronDown className="h-3 w-3" />
              </div>
            </div>

            {/* Heatmap preview */}
            <div className="relative w-full h-[125px] rounded-lg overflow-hidden border border-border-default/60 my-1 bg-bg-subtle">
              <Image
                src="/images/radar-heatmap.jpg"
                alt="US Jurisdiction Activity Radar Heatmap"
                fill
                className="object-cover object-center group-hover:scale-105 transition-transform duration-500"
                sizes="(max-width: 768px) 100vw, 320px"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-bg-elevated/80 via-transparent to-transparent" />
              <div className="absolute bottom-1.5 left-1.5 flex items-center gap-2 text-[9px] font-mono text-text-secondary bg-bg-elevated/90 px-1.5 py-0.5 rounded backdrop-blur-sm border border-border-default/40">
                <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-red-500" /> High</span>
                <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Med</span>
                <span className="flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Low</span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-border-default/60 grid grid-cols-3 gap-1 text-center">
            <div>
              <div className="font-mono text-body-sm font-bold text-text-primary">2,431</div>
              <div className="text-[10px] text-text-muted">Inquiries</div>
            </div>
            <div>
              <div className="font-mono text-body-sm font-bold text-info">312</div>
              <div className="text-[10px] text-text-muted">In Progress</div>
            </div>
            <div>
              <div className="font-mono text-body-sm font-bold text-success">1,802</div>
              <div className="text-[10px] text-text-muted">Resolved</div>
            </div>
          </div>
        </div>

        {/* Tile 2: Verified Attorney Consultations */}
        <div className="group relative flex flex-col justify-between overflow-hidden rounded-xl border border-border-default/80 bg-bg-elevated p-5 shadow-card transition-all duration-300 hover:border-accent/50 hover:shadow-card-lg">
          <div>
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 text-accent font-semibold text-body-sm">
                <Shield className="h-4 w-4" />
                <span>Verified Consultations</span>
              </div>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-0.5 text-[11px] font-mono text-text-muted hover:text-accent transition-colors"
              >
                <span>View All</span>
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>

            {/* Attorney List Items */}
            <div className="space-y-1.5 mt-2">
              {[
                { name: "Amanda Harrison", spec: "Civil Rights", initials: "AH" },
                { name: "Daniel Rivera", spec: "Police Misconduct", initials: "DR" },
                { name: "Jessica Marten", spec: "Environmental Law", initials: "JM" },
                { name: "Robert Chen", spec: "Constitutional Law", initials: "RC" },
              ].map((attorney, idx) => (
                <Link
                  key={idx}
                  href="/pricing"
                  className="flex items-center justify-between p-1.5 rounded-lg bg-bg-subtle/60 hover:bg-bg-subtle transition-colors border border-border-default/40 group/item"
                >
                  <div className="flex items-center gap-2">
                    <div className="h-6 w-6 rounded-full bg-accent/15 border border-accent/30 text-accent font-mono text-[10px] font-bold flex items-center justify-center shrink-0">
                      {attorney.initials}
                    </div>
                    <div className="min-w-0">
                      <div className="text-[11px] font-semibold text-text-primary truncate group-hover/item:text-accent transition-colors">
                        {attorney.name}
                      </div>
                      <div className="text-[9px] text-text-muted truncate">{attorney.spec}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-0.5 text-[9px] font-medium text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-1 py-0.5 rounded shrink-0">
                    <CheckCircle2 className="h-2.5 w-2.5" />
                    <span>Verified</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-border-default/60">
            <Link
              href="/pricing"
              className="inline-flex items-center justify-center gap-1 w-full text-center text-[11px] font-medium text-accent hover:text-accent-hover transition-colors"
            >
              <span>Connect with verified counsel</span>
              <ChevronRight className="h-3 w-3" />
            </Link>
          </div>
        </div>

        {/* Tile 3: Community Privacy Shield */}
        <div className="group relative flex flex-col justify-between overflow-hidden rounded-xl border border-border-default/80 bg-bg-elevated p-5 shadow-card transition-all duration-300 hover:border-accent/50 hover:shadow-card-lg">
          <div>
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 text-accent font-semibold text-body-sm">
                <Lock className="h-4 w-4" />
                <span>Community Privacy Shield</span>
              </div>
              <Link
                href="/privacy"
                className="inline-flex items-center gap-0.5 text-[11px] font-mono text-text-muted hover:text-accent transition-colors"
              >
                <span>Learn More</span>
                <ChevronRight className="h-3 w-3" />
              </Link>
            </div>

            {/* Interactive Toggle List */}
            <div className="space-y-1.5 mt-2">
              {[
                { key: "sanitizeHistory", label: "Sanitize search history", icon: Eye },
                { key: "securityToggles", label: "Security & data toggles", icon: Shield },
                { key: "communityAddress", label: "Community address obfuscation", icon: Globe },
                { key: "groupSecurity", label: "Group members protection", icon: Users },
                { key: "dataRedaction", label: "Data redaction tracking", icon: Database },
              ].map((item, idx) => {
                const isChecked = toggles[item.key as keyof typeof toggles];
                return (
                  <div
                    key={idx}
                    onClick={() => handleToggle(item.key as keyof typeof toggles)}
                    className="flex items-center justify-between p-1.5 rounded-lg bg-bg-subtle/50 hover:bg-bg-subtle cursor-pointer transition-colors border border-border-default/30"
                  >
                    <div className="flex items-center gap-1.5 min-w-0 pr-1">
                      <item.icon className="h-3 w-3 text-accent shrink-0" />
                      <span className="text-[10px] text-text-secondary truncate">{item.label}</span>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={isChecked}
                      className={`relative inline-flex h-3.5 w-7 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        isChecked ? "bg-accent" : "bg-border-strong"
                      }`}
                    >
                      <span
                        aria-hidden="true"
                        className={`pointer-events-none inline-block h-2.5 w-2.5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                          isChecked ? "translate-x-3.5" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-3 pt-2.5 border-t border-border-default/60">
            <div className="flex items-center justify-between text-[10px] text-text-muted font-mono">
              <span>Status: Protected</span>
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> 100% Active
              </span>
            </div>
          </div>
        </div>

        {/* Tile 4: Precinct Finder (matching Image 2) */}
        <div className="group relative flex flex-col justify-between overflow-hidden rounded-xl border border-border-default/80 bg-bg-elevated p-5 shadow-card transition-all duration-300 hover:border-accent/50 hover:shadow-card-lg">
          <div>
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 text-accent font-semibold text-body-sm">
                <Navigation className="h-4 w-4" />
                <span>Precinct Finder</span>
              </div>
              <span className="text-[10px] font-mono text-text-muted bg-bg-subtle px-1.5 py-0.5 rounded border border-border-default/40">
                Radar
              </span>
            </div>

            {/* Search input */}
            <div className="relative my-2">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-text-muted" />
              <input
                type="text"
                value={precinctQuery}
                onChange={(e) => setPrecinctQuery(e.target.value)}
                placeholder="Enter city, state or ZIP..."
                className="w-full rounded-md border border-border-default bg-bg-subtle/80 pl-7 pr-2 py-1.5 text-[11px] text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            {/* Map view with Pin & Controls */}
            <div className="relative w-full h-[115px] rounded-lg overflow-hidden border border-border-default/60 my-1 bg-bg-subtle">
              <Image
                src="/images/radar-heatmap.jpg"
                alt="Mapbox Precinct View"
                fill
                className="object-cover object-center"
                sizes="(max-width: 768px) 100vw, 320px"
              />
              <div className="absolute inset-0 bg-bg-elevated/45 backdrop-blur-[0.5px]" />
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-2">
                <MapPin className="h-5 w-5 text-accent animate-bounce mb-0.5" />
                <span className="text-[10px] font-mono font-medium text-text-primary bg-bg-elevated/95 px-2 py-0.5 rounded border border-border-default/40 shadow">
                  {precinctQuery ? precinctQuery : "Active Precinct Grid"}
                </span>
              </div>
              {/* Mapbox watermark & zoom controls */}
              <div className="absolute bottom-1 left-1.5 text-[8px] font-mono text-text-muted/80">
                mapbox
              </div>
              <div className="absolute right-1.5 top-1.5 flex flex-col gap-0.5 bg-bg-elevated/90 rounded border border-border-default/50 p-0.5">
                <button type="button" className="h-4 w-4 text-[10px] text-text-secondary hover:text-accent font-mono flex items-center justify-center">+</button>
                <div className="h-px bg-border-default/40" />
                <button type="button" className="h-4 w-4 text-[10px] text-text-secondary hover:text-accent font-mono flex items-center justify-center">-</button>
              </div>
            </div>
          </div>

          {/* Quick select tags */}
          <div className="mt-2 pt-2 border-t border-border-default/60 flex items-center justify-between gap-1">
            <span className="text-[9px] font-mono text-text-muted">Quick:</span>
            <div className="flex gap-1">
              {popularPrecincts.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setPrecinctQuery(p.label);
                    onSelectPrecinct?.(p.label);
                  }}
                  className="rounded bg-bg-subtle px-1.5 py-0.5 text-[9px] font-mono text-text-secondary hover:bg-accent/15 hover:text-accent border border-border-default/40 transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

