"use client";

import { BrainCircuit, History, Search } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

// Old RAG-search product's own workspace nav — retained, not extended,
// per the scope PDF. Only wraps the retired /search, /history, /upgrade
// routes ((protected)/layout.tsx); /account moved to a real, top-level
// route outside this group specifically so a real forum user reaching
// their own Account page never sees this old-product nav. The
// "Account" link was removed from here for the same reason: this bar
// has no real reason to link out of its own retired workspace into the
// current product's Account page.
const links = [
  { href: "/search", label: "Search", icon: Search },
  { href: "/history", label: "History", icon: History },
  { href: "/account/memory", label: "Memory", icon: BrainCircuit },
];

export function WorkspaceNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Your workspace" className="wp-workspace-nav">
      {links.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || (href === "/history" && pathname.startsWith("/search/"));
        return (
          <Link key={href} href={href} aria-current={active ? "page" : undefined}
            className={cn("wp-workspace-link", active && "wp-workspace-link-active")}>
            <Icon className="size-4" aria-hidden="true" />{label}
          </Link>
        );
      })}
    </nav>
  );
}
