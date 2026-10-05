"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Minimal footer — AgentGuide/00_SCOPE.md §2 (why.com's restraint: copyright,
 * Privacy, Terms, nothing else). Deliberately not a "SaaS mega-footer" with
 * six link columns — that's the exact generic pattern §2.2 of the Master
 * Prompt Guide bans.
 *
 * Forum rebuild, Milestone 2 Step M2.0: added the client's own verbatim
 * legal/trust disclaimer ("Not 911.") above the copyright line. Rendered
 * once here, in the root layout (see app/layout.tsx), so it appears on
 * EVERY page — the scope PDF's own UI Surfaces section only mentions this
 * disclaimer under "Home Feed," but a disclaimer of this kind belongs
 * everywhere a user can land, including the thread and attorney-portal
 * pages, not just the feed.
 */
import { Shield } from "lucide-react";

export function Footer() {
  const pathname = usePathname();
  const isAdminRoute = pathname === "/admin" || pathname.startsWith("/admin/");
  if (isAdminRoute) return null;

  return (
    <footer className="border-t border-border-default/70 bg-bg-surface/50 backdrop-blur-sm mt-auto">
      <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-8 py-10 flex flex-col items-center gap-6 text-body-sm text-text-muted">
        <div className="flex items-center gap-2 text-text-secondary">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/15 text-accent ring-1 ring-accent/30">
            <Shield className="h-3.5 w-3.5" />
          </div>
          <span className="font-serif font-medium text-text-primary">WhyPolice</span>
          <span className="text-border-strong">•</span>
          <span className="text-caption text-text-muted">Independent public archive &amp; community ledger. Not 911.</span>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 w-full border-t border-border-default/40 pt-6">
          <span className="text-caption">&copy; {new Date().getFullYear()} WhyPolice. All rights reserved.</span>
          <nav aria-label="Legal" className="flex items-center gap-6">
            <Link href="/pricing" className="text-caption hover:text-accent transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
              Pricing
            </Link>
            <Link href="/privacy" className="text-caption hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
              Privacy
            </Link>
            <Link href="/terms" className="text-caption hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
              Terms
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
