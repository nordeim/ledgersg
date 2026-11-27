"use client";

import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import {
  Menu,
  X,
  LayoutDashboard,
  FileText,
  PieChart,
  Settings,
  BookOpen,
  Receipt,
  Users,
  ChevronRight,
  ChevronDown,
  Building2,
  Check,
  Landmark,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";

/*
 * BRUTALIST LAYOUT SHELL
 * - Asymmetric grid ready
 * - Collapsible sidebar (mobile)
 * - Sticky header with blur backdrop
 * - Dynamic org context from auth provider
 */

interface ShellProps {
  children: React.ReactNode;
}

interface NavItem {
  icon: React.ElementType;
  label: string;
  href: string;
}

const navItems: NavItem[] = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: FileText, label: "Invoices", href: "/invoices" },
  { icon: Receipt, label: "Quotes", href: "/quotes" },
  { icon: Users, label: "Contacts", href: "/contacts" },
  { icon: BookOpen, label: "Ledger", href: "/ledger" },
  { icon: Landmark, label: "Banking", href: "/banking" },
  { icon: PieChart, label: "Reports", href: "/reports" },
  { icon: Settings, label: "Settings", href: "/settings" },
];

export function Shell({ children }: ShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [orgSelectorOpen, setOrgSelectorOpen] = useState(false);
  const pathname = usePathname();
  const { user, organisations, currentOrg, switchOrg, logout } = useAuth();

  // P12/A-1 overlay contract: the open mobile menu is a modal overlay —
  // body scroll locks and focus moves into the sidebar until it closes.
  const sidebarRef = useRef<HTMLElement | null>(null);
  const toggleRef = useRef<HTMLButtonElement | null>(null);
  const prevSidebarOpen = useRef(false);

  // P17/FE-L4: the org-selector is a menu (the Radix contract) —
  // container ref for outside-click, trigger ref for focus return.
  const orgMenuRef = useRef<HTMLDivElement | null>(null);
  const orgTriggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!sidebarOpen) return;
    document.body.style.overflow = "hidden";
    const firstFocus =
      sidebarRef.current?.querySelector<HTMLElement>("#main-navigation a") ??
      sidebarRef.current;
    firstFocus?.focus();
    return () => {
      document.body.style.overflow = "";
    };
  }, [sidebarOpen]);

  // P16/FE-M2: while the drawer is open below md, crossing INTO the md
  // breakpoint (rotate/resize) hides the overlay and the X toggle (both
  // md:hidden) — the scroll lock would persist with no visible escape.
  // Close the drawer at the crossing; the effect above releases the lock.
  useEffect(() => {
    if (!sidebarOpen) return;
    const mql = window.matchMedia("(min-width: 768px)");
    const onCross = (e: MediaQueryListEvent) => {
      if (e.matches) setSidebarOpen(false);
    };
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", onCross);
      return () => mql.removeEventListener("change", onCross);
    }
    // Legacy API fallback
    mql.addListener(onCross);
    return () => mql.removeListener(onCross);
  }, [sidebarOpen]);

  // Escape closes the overlay; Tab cycles within it (focus trap).
  useEffect(() => {
    if (!sidebarOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        // P18/FE-M1: the org menu lives inside the drawer — when it is
        // open, IT consumes the first Escape (closing itself and
        // returning focus to the trigger, still visible). Handling it
        // here too would close the drawer AND strand focus on the
        // trigger inside the now-invisible drawer in one keystroke.
        if (orgSelectorOpen) return;
        e.preventDefault();
        setSidebarOpen(false);
        return;
      }
      if (e.key !== "Tab") return;
      const aside = sidebarRef.current;
      if (!aside) return;
      // P16/FE-L4: the full focusable set — a[href]/button alone would
      // let any future form control in the drawer escape the trap.
      // (No visibility filter: jsdom has no layout — the drawer is
      // visible whenever this trap is active.)
      const focusables = Array.from(
        aside.querySelectorAll<HTMLElement>(
          "a[href], button:not([disabled]), input:not([disabled]), " +
            "select:not([disabled]), textarea:not([disabled]), " +
            '[tabindex]:not([tabindex="-1"]):not([disabled])'
        )
      );
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;
      const inSidebar = active !== null && aside.contains(active);
      if (!e.shiftKey && (!inSidebar || active === last)) {
        e.preventDefault();
        first.focus();
      } else if (e.shiftKey && (!inSidebar || active === first)) {
        e.preventDefault();
        last.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [sidebarOpen, orgSelectorOpen]);

  // Focus returns to the trigger when the overlay closes (P12/A-1).
  useEffect(() => {
    if (prevSidebarOpen.current && !sidebarOpen) {
      toggleRef.current?.focus();
    }
    prevSidebarOpen.current = sidebarOpen;
  }, [sidebarOpen]);

  const isActiveRoute = (href: string) => {
    if (href === "/dashboard") {
      return pathname === "/dashboard" || pathname === "/";
    }
    return pathname?.startsWith(href);
  };

  const handleOrgSwitch = (orgId: string) => {
    switchOrg(orgId);
    setOrgSelectorOpen(false);
    orgTriggerRef.current?.focus();
  };

  // P17/FE-L4: keyboard + focus contract for the org-selector menu.
  // Open: focus lands on the current org's item (the drawer exemplar
  // moves focus into the overlay). While open: Escape closes and
  // returns focus to the trigger; arrows/Home/End rove with wrap;
  // pointerdown outside the container closes. The menu itself stays
  // mounted (hidden) so the trigger's aria-controls is always valid.
  useEffect(() => {
    if (!orgSelectorOpen) return;
    const container = orgMenuRef.current;
    const items = container
      ? Array.from(
          container.querySelectorAll<HTMLElement>('[role^="menuitem"]')
        )
      : [];
    (
      items.find((i) => i.getAttribute("aria-checked") === "true") ??
        items[0]
    )?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setOrgSelectorOpen(false);
        orgTriggerRef.current?.focus();
        return;
      }
      if (
        e.key !== "ArrowDown" &&
        e.key !== "ArrowUp" &&
        e.key !== "Home" &&
        e.key !== "End"
      ) {
        return;
      }
      const menuItems = container
        ? Array.from(
            container.querySelectorAll<HTMLElement>('[role^="menuitem"]')
          )
        : [];
      if (menuItems.length === 0) return;
      e.preventDefault();
      const active = document.activeElement;
      const idx =
        active instanceof HTMLElement ? menuItems.indexOf(active) : -1;
      let next: HTMLElement;
      if (e.key === "Home") {
        next = menuItems[0];
      } else if (e.key === "End") {
        next = menuItems[menuItems.length - 1];
      } else if (e.key === "ArrowDown") {
        next = menuItems[(idx + 1 + menuItems.length) % menuItems.length];
      } else {
        next = menuItems[(idx - 1 + menuItems.length) % menuItems.length];
      }
      next.focus();
    };
    const onPointerDown = (e: MouseEvent) => {
      if (container && !container.contains(e.target as Node)) {
        setOrgSelectorOpen(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, [orgSelectorOpen]);

  // Get user initials for avatar
  const userInitials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "DU";

  return (
    <div className="min-h-screen bg-void text-text-primary flex">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-void/80 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        tabIndex={-1}
        // P16/FE-L5: the open drawer behaves as a modal (focus trap,
        // scroll lock, overlay) — expose the semantics. Desktop md+ is a
        // persistent sidebar, so the dialog role applies only while the
        // mobile drawer is open.
        role={sidebarOpen ? "dialog" : undefined}
        aria-modal={sidebarOpen ? "true" : undefined}
        aria-label={sidebarOpen ? "Navigation" : undefined}
        className={cn(
          "fixed md:sticky top-0 h-screen w-64 bg-carbon border-r border-border z-50",
          // P13/H-2: the closed drawer is visibility-hidden below md — a
          // transform alone leaves the off-screen focusables in the tab
          // order (WCAG 2.4.3/2.4.7). visibility is discretely-animatable:
          // with it on the transition, closing stays visible through the
          // slide-out and flips to hidden at the end; opening flips
          // visible immediately.
          //
          // P23/FE-M1: `translate` MUST be in the list — Tailwind v4
          // renders translate-x-* through the STANDALONE `translate` CSS
          // property (not `transform: matrix(...)`), so a transform-only
          // list compiled to `transition-property: transform,visibility`
          // and the 300ms slide snapped (open/close still worked — the
          // animation was dead config; Trap 5(b) in
          // docs/Tailwind-V4-Validation-Report.md). `transform` stays for
          // matrix-engine robustness, `visibility` for the discrete hide.
          "transition-[transform,translate,visibility] duration-300 ease-in-out",
          sidebarOpen
            ? "translate-x-0"
            : "-translate-x-full md:translate-x-0 invisible md:visible"
        )}
      >
        {/* Logo Section */}
        <div className="p-6 border-b border-border">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-accent-primary flex items-center justify-center rounded-sm">
              <span className="font-mono font-bold text-void text-lg">L</span>
            </div>
            {/* P20/FE-L2: the brand is a paragraph, not a heading — every
                dashboard page renders the page's own h1; a second h1 in
                the sidebar logo broke the one-h1-per-page contract. */}
            <p className="font-display text-xl font-bold tracking-tight">
              LEDGER<span className="text-accent-primary">SG</span>
            </p>
          </Link>
          <p className="text-xs text-text-muted mt-1 font-mono">
            IRAS-Compliant Accounting
          </p>
        </div>

        {/* Navigation */}
        {/* P7/F-16: id matches the mobile toggle's aria-controls. */}
        <nav id="main-navigation" className="p-4 space-y-1" aria-label="Main navigation">
          {navItems.map((item) => {
            const isActive = isActiveRoute(item.href);
            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors rounded-sm",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary/50",
                  isActive
                    ? "bg-surface text-accent-primary border-l-2 border-accent-primary"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <item.icon className="h-4 w-4" aria-hidden="true" />
                <span>{item.label}</span>
                {isActive && (
                  <ChevronRight className="h-4 w-4 ml-auto" aria-hidden="true" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer: User & Org Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border">
          {/* Org Selector (P17/FE-L4: the Radix menu contract — aria
              state on the trigger, Escape/outside-click close,
              arrow-key navigation with wrap-around) */}
          {currentOrg && organisations.length > 0 && (
            <div className="mb-3" ref={orgMenuRef}>
              <button
                id="org-selector-trigger"
                ref={orgTriggerRef}
                onClick={() => setOrgSelectorOpen(!orgSelectorOpen)}
                onKeyDown={(e) => {
                  // Radix contract: vertical arrows on the closed
                  // trigger open the menu (focus effect takes over).
                  if (
                    !orgSelectorOpen &&
                    (e.key === "ArrowDown" || e.key === "ArrowUp")
                  ) {
                    e.preventDefault();
                    setOrgSelectorOpen(true);
                  }
                }}
                aria-label="Switch organisation"
                aria-haspopup="menu"
                aria-expanded={orgSelectorOpen}
                aria-controls="org-selector-menu"
                className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors rounded-sm hover:bg-surface"
              >
                <Building2 className="h-3 w-3" aria-hidden="true" />
                <span className="truncate flex-1 text-left">
                  {currentOrg.name}
                </span>
                <ChevronDown
                  className={cn(
                    "h-3 w-3 transition-transform",
                    orgSelectorOpen && "rotate-180"
                  )}
                  aria-hidden="true"
                />
              </button>

              {/* Org Dropdown — stays mounted (hidden when closed) so
                  the trigger's aria-controls id always resolves. */}
              <div
                id="org-selector-menu"
                role="menu"
                aria-labelledby="org-selector-trigger"
                hidden={!orgSelectorOpen}
                className="mt-1 py-1 bg-surface border border-border rounded-sm shadow-lg"
              >
                {organisations.map((uo) => (
                  <button
                    key={uo.org.id}
                    role="menuitemradio"
                    aria-checked={uo.org.id === currentOrg.id}
                    tabIndex={-1}
                    onClick={() => handleOrgSwitch(uo.org.id)}
                    className={cn(
                      "w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-carbon transition-colors",
                      uo.org.id === currentOrg.id && "text-accent-primary"
                    )}
                  >
                    <span className="truncate flex-1 text-left">
                      {uo.org.name}
                    </span>
                    {uo.org.id === currentOrg.id && (
                      <Check className="h-3 w-3" aria-hidden="true" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* User Info */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-surface rounded-sm flex items-center justify-center">
              <span className="text-xs font-mono text-text-secondary">
                {userInitials}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {user?.full_name || "Member"}
              </p>
              <p className="text-xs text-text-muted font-mono truncate">
                {user?.email || ""}
              </p>
            </div>
            {/* Session end affordance (P4/E-1): the persisted session needs
                a UI kill switch — logout blacklists the refresh cookie and
                expires it server-side. */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 flex-shrink-0 text-text-muted hover:text-alert"
              onClick={() => void logout()}
              aria-label="Log out"
              title="Log out"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        {/* P13/M-1: z-50 — the header must paint ABOVE the z-40 mobile
            overlay so the X ("Close navigation") toggle stays clickable
            while the menu is open (it follows the aside in DOM order, so
            equal z-index paints it on top). */}
        <header className="sticky top-0 z-50 flex h-16 items-center gap-4 border-b border-border bg-void/90 backdrop-blur supports-[backdrop-filter]:bg-void/80 px-4 md:px-6">
          {/* Mobile Menu Toggle */}
          <Button
            ref={toggleRef}
            variant="ghost"
            size="icon"
            className="md:hidden h-9 w-9"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label={sidebarOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={sidebarOpen}
            aria-controls="main-navigation"
          >
            {sidebarOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </Button>

          {/* Breadcrumb / Page Title — a visual label, not a heading: each
              page already owns its h1, and a second same-text heading
              duplicated the document outline (and strict-mode-resolved
              twice in e2e). */}
          <div className="flex-1 min-w-0">
            <div
              aria-hidden="true"
              className="text-lg font-display font-semibold text-text-primary truncate"
            >
              {navItems.find((item) => isActiveRoute(item.href))?.label ||
                "LedgerSG"}
            </div>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* P7/F-17: was a dead button with no handler — now a real
                link to the new-invoice form. */}
            <Link
              href="/invoices/new"
              className="hidden sm:inline-flex h-9 items-center rounded-sm border border-border px-3 text-sm text-text-secondary transition-colors hover:bg-surface hover:text-text-primary"
            >
              <Receipt className="h-4 w-4 mr-2" />
              New Invoice
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl space-y-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
