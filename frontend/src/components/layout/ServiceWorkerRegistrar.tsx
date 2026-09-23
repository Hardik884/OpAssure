"use client";

/** Registers the app-shell service worker (public/sw.js). Renders nothing. */
import { useEffect } from "react";

export function ServiceWorkerRegistrar() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Non-fatal — the app works fully online without it; this only improves offline behavior.
    });
  }, []);

  return null;
}
