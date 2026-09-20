import Link from "next/link";

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
export function Footer() {
  return (
    <footer className="border-t border-border-default mt-auto">
      <div className="mx-auto max-w-[1200px] px-5 sm:px-6 py-7 flex flex-col items-center gap-4 text-body-sm text-text-muted">
        <p className="text-center">
          WhyPolice.com is an independent public archive &amp; forum. Not 911.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 w-full">
          <span>&copy; {new Date().getFullYear()} WhyPolice. All rights reserved.</span>
          <nav aria-label="Legal" className="flex items-center gap-5">
            <Link href="/privacy" className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
              Terms
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
