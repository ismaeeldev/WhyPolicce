"use client";

import { useUser } from "@auth0/nextjs-auth0";
import { BrainCircuit, History, LogOut, Menu, User as UserIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

const NAV_LINKS = [
  { href: "/about", label: "About" },
  { href: "/pricing", label: "Pricing" },
];

/**
 * Persistent top nav — AgentGuide/01_ThemeGuideline.md §4.1. Transparent at
 * the hero top, gains a hairline border once the page scrolls, per spec.
 * Auth-aware slot per AgentGuide/03_MasterPromptGuide.md Step 3: logged-out
 * shows Log in/Sign up, logged-in shows avatar + dropdown (Account, Logout),
 * with a skeleton per ThemeGuideline §4.9 while the session resolves.
 */
export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, isLoading } = useUser();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-30 bg-bg/90 backdrop-blur-sm transition-colors duration-200 ${
        scrolled ? "border-b border-border-default" : "border-b border-transparent"
      }`}
    >
      <div className="mx-auto max-w-[1200px] px-6 h-16 flex items-center justify-between">
        <Link href="/" className="font-display text-xl text-text-primary focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm">
          WhyPolice
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="group relative text-body-sm text-text-secondary hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none rounded-sm"
            >
              {link.label}
              <span className="absolute -bottom-1 left-0 h-px w-0 bg-accent transition-all duration-200 ease-out group-hover:w-full" />
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-2">
          <ThemeToggle />
          {isLoading ? (
            <Skeleton className="h-9 w-9 rounded-full" />
          ) : user ? (
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <button
                    type="button"
                    aria-label="Account menu"
                    className="rounded-full focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                  />
                }
              >
                <Avatar className="h-9 w-9">
                  <AvatarImage src={user.picture} alt={user.name ?? "Account"} />
                  <AvatarFallback>
                    {(user.name ?? user.email ?? "?").charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <div className="px-2 py-1.5 text-body-sm text-text-secondary truncate">
                  {user.email ?? user.name}
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem render={<Link href="/history" />} className="flex items-center gap-2">
                  <History className="h-4 w-4" />
                  History
                </DropdownMenuItem>
                <DropdownMenuItem render={<Link href="/account" />} className="flex items-center gap-2">
                  <UserIcon className="h-4 w-4" />
                  Account
                </DropdownMenuItem>
                <DropdownMenuItem render={<Link href="/account/memory" />} className="flex items-center gap-2">
                  <BrainCircuit className="h-4 w-4" />
                  Memory
                </DropdownMenuItem>
                <DropdownMenuItem render={<a href="/auth/logout" />} className="flex items-center gap-2">
                  <LogOut className="h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-sm px-3.5 py-2 text-body-sm text-text-secondary hover:bg-bg-subtle hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="rounded-sm bg-accent px-4 py-2 text-body-sm font-medium text-accent-foreground hover:bg-accent-hover transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
              >
                Sign up
              </Link>
            </>
          )}
        </div>

        {/* Mobile: hamburger -> slide-down sheet, per ThemeGuideline §4.1 */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <button
            type="button"
            aria-label="Open menu"
            onClick={() => setMobileOpen(true)}
            className="md:hidden flex h-9 w-9 items-center justify-center rounded-sm hover:bg-bg-subtle transition-colors focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
          >
            <Menu className="h-5 w-5" />
          </button>
          <SheetContent side="top" className="bg-bg border-border-default">
            <SheetHeader>
              <SheetTitle className="font-display text-lg">WhyPolice</SheetTitle>
            </SheetHeader>
            <div className="flex flex-col gap-1 px-4 pb-4">
              <div className="mb-2 flex items-center justify-between px-2 py-1">
                <span className="text-body-sm text-text-muted">Appearance</span>
                <ThemeToggle />
              </div>
              {NAV_LINKS.map((link) => (
                <SheetClose
                  key={link.href}
                  render={
                    <Link
                      href={link.href}
                      className="rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                    />
                  }
                >
                  <span className="block rounded-sm px-2 py-2.5 text-body text-text-primary hover:bg-bg-subtle transition-colors">
                    {link.label}
                  </span>
                </SheetClose>
              ))}
              {user ? (
                <div className="mt-2 flex flex-col gap-2">
                  <SheetClose
                    render={
                      <Link
                        href="/history"
                        className="rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                      />
                    }
                  >
                    <span className="block rounded-sm border border-border-strong px-4 py-2.5 text-center text-body text-text-primary hover:bg-bg-subtle transition-colors">
                      History
                    </span>
                  </SheetClose>
                  <SheetClose
                    render={
                      <Link
                        href="/account"
                        className="rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                      />
                    }
                  >
                    <span className="block rounded-sm border border-border-strong px-4 py-2.5 text-center text-body text-text-primary hover:bg-bg-subtle transition-colors">
                      Account
                    </span>
                  </SheetClose>
                  <SheetClose
                    render={
                      <Link
                        href="/account/memory"
                        className="rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                      />
                    }
                  >
                    <span className="block rounded-sm border border-border-strong px-4 py-2.5 text-center text-body text-text-primary hover:bg-bg-subtle transition-colors">
                      Memory
                    </span>
                  </SheetClose>
                  <SheetClose
                    render={
                      <a
                        href="/auth/logout"
                        className="rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                      />
                    }
                  >
                    <span className="block rounded-sm bg-accent px-4 py-2.5 text-center text-body font-medium text-accent-foreground hover:bg-accent-hover transition-colors">
                      Log out
                    </span>
                  </SheetClose>
                </div>
              ) : (
                <div className="mt-2 flex flex-col gap-2">
                  <SheetClose
                    render={
                      <Link
                        href="/login"
                        className="rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                      />
                    }
                  >
                    <span className="block rounded-sm border border-border-strong px-4 py-2.5 text-center text-body text-text-primary hover:bg-bg-subtle transition-colors">
                      Log in
                    </span>
                  </SheetClose>
                  <SheetClose
                    render={
                      <Link
                        href="/signup"
                        className="rounded-sm focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 outline-none"
                      />
                    }
                  >
                    <span className="block rounded-sm bg-accent px-4 py-2.5 text-center text-body font-medium text-accent-foreground hover:bg-accent-hover transition-colors">
                      Sign up
                    </span>
                  </SheetClose>
                </div>
              )}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
