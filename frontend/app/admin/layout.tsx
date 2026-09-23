"use client";

import { LayoutDashboard, Scale, ShieldAlert, Flag } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Skeleton } from "@/components/ui/skeleton";
import { useAdminMe } from "@/hooks/useAdmin";

const NAV_ITEMS = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/admin/attorneys", label: "Attorneys", icon: Scale, exact: false },
  { href: "/admin/reports", label: "Reports", icon: Flag, exact: false },
];

/**
 * Admin panel shell — new admin panel (client's explicit request).
 * Deliberately a DISTINCT internal-tool layout (persistent sidebar,
 * dense tables) rather than reusing the public forum's card-based
 * pages, but built entirely from this app's existing design tokens
 * (--accent, --bg-elevated, --border-default, etc.) so it's
 * unmistakably WhyPolice, not a bolted-on separate product.
 *
 * Security model: proxy.ts already enforces "must be logged in" for
 * the whole /admin prefix (a logged-out visitor never reaches this
 * component at all — they're redirected to /login first). This layout
 * adds the REAL admin-membership check on top, via GET /api/v1/admin/me
 * (backed by the server-side ADMIN_AUTH0_SUBS allowlist) — a logged-in
 * non-admin gets a clear, real "not authorized" screen here, never a
 * silent redirect or a raw API 403 bubbling up from some nested
 * component. This is a UI-only convenience gate; the actual security
 * boundary is every individual admin endpoint's own server-side
 * _require_admin check, already independently tested.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: me, isLoading } = useAdminMe();
  const pathname = usePathname();

  if (isLoading) {
    return (
      <div className="flex min-h-[calc(100vh-5rem)] w-full">
        <div className="hidden w-64 shrink-0 border-r border-border-default bg-bg-elevated p-4 md:block">
          <Skeleton className="h-8 w-32 mb-6" />
          <div className="flex flex-col gap-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </div>
        <div className="flex-1 p-6 sm:p-8">
          <Skeleton className="h-9 w-48 mb-6" />
          <Skeleton className="h-40 w-full rounded-md" />
        </div>
      </div>
    );
  }

  if (!me?.isAdmin) {
    return (
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-[560px] flex-col items-center justify-center px-5 text-center">
        <ShieldAlert className="h-10 w-10 text-text-muted mb-4" strokeWidth={1.5} />
        <h1 className="font-display text-h2 text-text-primary mb-2">Not authorized</h1>
        <p className="text-body-sm text-text-secondary max-w-sm">
          This account doesn&apos;t have admin access. If you believe this is a mistake, contact
          whoever manages the WhyPolice admin allowlist.
        </p>
        <Link
          href="/"
          className="mt-6 rounded-sm border border-border-strong px-4 py-2 text-body-sm font-medium text-text-primary transition-colors hover:bg-bg-subtle focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
        >
          Back to the forum
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-5rem)] w-full">
      <aside className="hidden w-64 shrink-0 border-r border-border-default bg-bg-elevated md:flex md:flex-col">
        <div className="border-b border-border-default px-5 py-5">
          <p className="font-display text-lg text-text-primary">Admin</p>
          <p className="text-caption text-text-muted truncate">{me.email}</p>
        </div>
        <nav aria-label="Admin navigation" className="flex flex-col gap-1 p-3">
          {NAV_ITEMS.map((item) => {
            const isActive = item.exact ? pathname === item.href : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={`flex items-center gap-2.5 rounded-sm px-3 py-2.5 text-body-sm transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
                  isActive
                    ? "bg-accent-subtle text-text-primary font-medium"
                    : "text-text-secondary hover:bg-bg-subtle hover:text-text-primary"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Mobile: a simple top tab strip instead of a slide-in sheet —
          the admin panel's own nav is only 3 items, so a full mobile
          drawer pattern (matching the public Navbar's own) would be
          more mechanism than this small a nav needs. */}
      <nav
        aria-label="Admin navigation"
        className="fixed inset-x-0 top-20 z-20 flex items-center gap-1 border-b border-border-default bg-bg-elevated px-3 py-2 md:hidden"
      >
        {NAV_ITEMS.map((item) => {
          const isActive = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`rounded-sm px-3 py-1.5 text-caption font-medium transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none ${
                isActive ? "bg-accent-subtle text-text-primary" : "text-text-secondary hover:bg-bg-subtle"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      <main className="min-w-0 flex-1 px-5 py-6 sm:px-8 sm:py-8 md:pt-8 pt-16">{children}</main>
    </div>
  );
}
