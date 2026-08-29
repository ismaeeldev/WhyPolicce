import Link from "next/link";

/**
 * Minimal footer — AgentGuide/00_SCOPE.md §2 (why.com's restraint: copyright,
 * Privacy, Terms, nothing else). Deliberately not a "SaaS mega-footer" with
 * six link columns — that's the exact generic pattern §2.2 of the Master
 * Prompt Guide bans.
 */
export function Footer() {
  return (
    <footer className="border-t border-border-default mt-auto">
      <div className="mx-auto max-w-[1200px] px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-body-sm text-text-muted">
        <span>&copy; {new Date().getFullYear()} WhyPolice. All rights reserved.</span>
        <nav className="flex items-center gap-5">
          <Link href="/privacy" className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
            Terms
          </Link>
        </nav>
      </div>
    </footer>
  );
}
