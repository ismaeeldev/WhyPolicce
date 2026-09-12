"use client";

import { BrainCircuit, History, Search, UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/search", label: "Search", icon: Search },
  { href: "/history", label: "History", icon: History },
  { href: "/account/memory", label: "Memory", icon: BrainCircuit },
  { href: "/account", label: "Account", icon: UserRound },
];

export function WorkspaceNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Your workspace" className="wp-workspace-nav">
      {links.map(({ href, label, icon: Icon }) => {
        const active = href === "/account"
          ? pathname === href || pathname.startsWith("/account/billing") || pathname === "/upgrade"
          : pathname === href || (href === "/history" && pathname.startsWith("/search/"));
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
