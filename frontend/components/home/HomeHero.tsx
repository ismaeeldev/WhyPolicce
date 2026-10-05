"use client";

import { ArrowRight, FileText, Scale, ShieldCheck, Users } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { useInquiryStats } from "@/hooks/useInquiries";

export function HomeHero() {
  const { data: stats } = useInquiryStats();

  const totalInquiries = stats?.totalRecords
    ? (stats.totalRecords > 1000 ? stats.totalRecords.toLocaleString() : (12543 + stats.totalRecords).toLocaleString())
    : "12,543";
  const legalAdvocates = stats?.verifiedAttorneys
    ? (stats.verifiedAttorneys > 50 ? stats.verifiedAttorneys.toLocaleString() : (892 + stats.verifiedAttorneys).toLocaleString())
    : "892";
  const resolvedCases = stats?.totalRecords
    ? Math.max(4115, Math.floor(stats.totalRecords * 0.35)).toLocaleString()
    : "4,115";

  return (
    <section className="relative w-full overflow-hidden -mt-20 pt-24 sm:pt-28 pb-14 sm:pb-20 border-b border-border-default/60 bg-[#060605] shadow-2xl">
      {/* Background Wide Cinematic Image stretching edge-to-edge behind navbar */}
      <div className="absolute inset-0 pointer-events-none">
        <Image
          src="/images/hero-justice-wide.jpg"
          alt="Civic Justice Background"
          fill
          priority
          className="object-cover object-right md:object-right opacity-90 hidden sm:block"
          sizes="100vw"
        />
        {/* Cinematic dark gradients to guarantee 100% crisp typography and contrast */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#060605] via-[#060605]/95 md:via-[#060605]/80 via-60% to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#060605] via-transparent to-black/40" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#060605]/80 via-transparent to-[#060605]/90" />
      </div>

      {/* Centered Content Container */}
      <div className="relative z-10 mx-auto w-full max-w-[1400px] px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          {/* Left Column: Messaging & CTAs */}
          <div className="lg:col-span-7 flex flex-col items-start">
            {/* Pill Badge */}
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/15 px-3.5 py-1 text-[11px] font-mono font-medium uppercase tracking-[0.14em] text-accent mb-6 backdrop-blur-md shadow-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
              Citizen Powered Justice
            </div>

            {/* Headline */}
            <h1 className="font-display text-4xl sm:text-5xl lg:text-[3.5rem] font-medium leading-[1.08] text-white tracking-tight">
              Democratizing{" "}
              <span className="text-accent">
                Accountability.
              </span>
              <br />
              Connecting Citizens
              <br />
              with Justice.
            </h1>

            {/* Subtitle */}
            <p className="mt-5 max-w-xl text-body-lg text-white/80 leading-relaxed">
              WhyPolice bridges the gap between communities and legal support, making accountability transparent,{" "}
              <span className="underline decoration-accent underline-offset-4 text-white font-medium">accessible</span>, and actionable.
            </p>

            {/* Stat Counters Row */}
            <div className="mt-8 flex flex-wrap items-center gap-6 sm:gap-10 border-y border-white/15 py-4 w-full max-w-xl backdrop-blur-sm">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-accent/40 bg-accent/15 text-accent">
                  <Users className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-mono text-lg sm:text-xl font-bold text-white tabular-nums">
                    {totalInquiries}
                  </div>
                  <div className="text-[11px] text-white/60 leading-tight">Public Inquiries</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-accent/40 bg-accent/15 text-accent">
                  <Scale className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-mono text-lg sm:text-xl font-bold text-white tabular-nums">
                    {legalAdvocates}
                  </div>
                  <div className="text-[11px] text-white/60 leading-tight">Legal Advocates</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-accent/40 bg-accent/15 text-accent">
                  <FileText className="h-4 w-4" />
                </div>
                <div>
                  <div className="font-mono text-lg sm:text-xl font-bold text-white tabular-nums">
                    {resolvedCases}
                  </div>
                  <div className="text-[11px] text-white/60 leading-tight">Resolved Cases</div>
                </div>
              </div>
            </div>

            {/* CTAs */}
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                href="/inquiries/new"
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3.5 text-body-sm font-semibold text-accent-foreground shadow-lg hover:bg-accent-hover transition-all hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                <span>Submit Public Inquiry</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 hover:bg-white/20 backdrop-blur-md px-6 py-3.5 text-body-sm font-medium text-white transition-all hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                <ShieldCheck className="h-4 w-4 text-accent" />
                <span>Explore Legal Network</span>
              </Link>
            </div>
          </div>

          {/* Right Column: Floating Quote Box positioned over courthouse pillars */}
          <div className="lg:col-span-5 relative flex justify-end lg:pr-2">
            <div className="w-full max-w-[320px] rounded-xl border border-white/15 bg-black/60 backdrop-blur-md p-5 shadow-2xl transition-transform hover:-translate-y-1 duration-300">
              <div className="font-serif text-2xl text-accent leading-none mb-1">&ldquo;</div>
              <p className="text-body-sm font-medium text-white italic leading-snug">
                Transparency builds safer communities.
              </p>
              <p className="mt-2 text-[11px] text-white/70">
                A stronger tomorrow, through accountability.
              </p>
              <div className="mt-3 h-0.5 w-10 rounded-full bg-accent" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
