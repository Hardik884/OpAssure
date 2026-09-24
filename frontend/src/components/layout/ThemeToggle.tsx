"use client";

/** Compact header control — not a settings page. Icon + accessible label, keyboard reachable. */
import { useEffect, useState } from "react";

import { MoonIcon, SunToggleIcon } from "@/components/common/icons";

import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  // The server always renders the light default (it can't see localStorage). Gating the
  // theme-dependent label/icon behind a mount flag avoids a hydration mismatch that could
  // otherwise leave this button's aria-label/aria-pressed stuck on the server's guess when a
  // dark preference is stored — mount detection has no synchronous alternative here.
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    // Mount detection has no synchronous alternative — this effect only ever runs once.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  const isDark = mounted && theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      aria-pressed={isDark}
      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-industrial border border-white/15 text-white transition-colors hover:border-white/35 hover:bg-white/10"
    >
      <span aria-hidden suppressHydrationWarning>
        {isDark ? <SunToggleIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
      </span>
    </button>
  );
}
