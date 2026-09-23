"use client";

/**
 * Light/dark mode. Light is the default, matching the app's existing approved
 * look; dark is a deliberate industrial dark interface (see globals.css), never
 * a naive inversion. Persisted to localStorage; applied via `data-theme` on
 * <html> so every semantic token in globals.css switches at once.
 *
 * The inline script in app/layout.tsx sets `data-theme` before hydration (from
 * the same localStorage key) to avoid a flash of the wrong theme; this provider
 * only needs to read that already-applied value on mount, then own it for toggling.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import type { ThemeMode } from "@/types";

const STORAGE_KEY = "opassure-theme";

interface ThemeContextValue {
  theme: ThemeMode;
  toggleTheme: () => void;
}

const Context = createContext<ThemeContextValue | null>(null);

function applyTheme(theme: ThemeMode) {
  document.documentElement.setAttribute("data-theme", theme);
}

function readInitialTheme(): ThemeMode {
  if (typeof document === "undefined") return "light"; // SSR — client re-reads on mount below
  const attr = document.documentElement.getAttribute("data-theme");
  if (attr === "dark" || attr === "light") return attr;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light") return stored;
  } catch {
    // localStorage unavailable (private mode, etc.) — fall through to the light default.
  }
  return "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  // Light by default; the inline anti-flash script may have already set dark on
  // <html> before this ever mounts — this lazy initializer reads that back so
  // React and the DOM agree from the very first render (no effect needed).
  const [theme, setTheme] = useState<ThemeMode>(readInitialTheme);

  useEffect(() => {
    applyTheme(theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Non-fatal — the toggle still works for the current page load.
    }
  }, [theme]);

  const toggleTheme = () => setTheme((prev) => (prev === "light" ? "dark" : "light"));

  return <Context.Provider value={{ theme, toggleTheme }}>{children}</Context.Provider>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(Context);
  if (!value) throw new Error("useTheme must be used within ThemeProvider");
  return value;
}

/** Source string for the pre-hydration inline script in app/layout.tsx. */
export const THEME_ANTI_FLASH_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem("${STORAGE_KEY}");
    if (stored === "dark") document.documentElement.setAttribute("data-theme", "dark");
  } catch (e) {}
})();
`;
