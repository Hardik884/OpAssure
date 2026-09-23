"use client";

/**
 * Primary navigation, rendered two ways from one config so it never drifts:
 *   - tablet/desktop: horizontal bar under the header
 *   - phone: fixed bottom tab bar (thumb-reachable, matches field-app conventions)
 * Both use large touch targets and an unmistakable active state (yellow, not just tint).
 */
import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "./navItems";

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Nav() {
  const pathname = usePathname();

  return (
    <>
      {/* Tablet / desktop: horizontal bar */}
      <nav
        aria-label="Primary"
        className="sticky top-16 z-20 hidden border-b-2 border-ink-950 bg-ink-900 sm:block"
      >
        <div className="mx-auto flex w-full max-w-6xl items-stretch px-2 sm:px-4">
          {NAV_ITEMS.map(({ key, label, href, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={key}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-12 flex-1 items-center justify-center gap-2 border-b-4 px-3 text-sm font-bold uppercase tracking-wide transition-colors ${
                  active
                    ? "border-brand-500 text-brand-500"
                    : "border-transparent text-line-400 hover:text-white"
                }`}
              >
                <Icon className="h-5 w-5 shrink-0" aria-hidden />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Phone: fixed bottom tab bar */}
      <nav
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-30 border-t-2 border-ink-950 bg-ink-900 sm:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        <div className="flex items-stretch">
          {NAV_ITEMS.map(({ key, label, href, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={key}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-16 flex-1 flex-col items-center justify-center gap-0.5 px-0.5 text-[10px] font-bold uppercase leading-none ${
                  active ? "text-brand-500" : "text-line-400"
                }`}
              >
                <Icon className="h-6 w-6 shrink-0" aria-hidden />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
