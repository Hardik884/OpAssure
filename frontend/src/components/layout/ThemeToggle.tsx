"use client";

/** Compact header control — not a settings page. Icon + accessible label, keyboard reachable. */
import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      aria-pressed={isDark}
      className="flex h-11 w-11 shrink-0 items-center justify-center rounded-industrial border-2 border-white/20 text-lg text-white transition-colors hover:border-white/40 hover:bg-white/10"
    >
      {/* The stored theme can differ from the server's light default — this icon alone may
          legitimately differ between server and first client render (see ThemeProvider). */}
      <span aria-hidden suppressHydrationWarning>
        {isDark ? "☀" : "🌙"}
      </span>
    </button>
  );
}
