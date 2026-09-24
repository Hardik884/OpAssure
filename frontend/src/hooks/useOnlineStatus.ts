"use client";

/**
 * Real browser connectivity — never a stand-in for the WebSocket's live/demo mode.
 *
 * `online`/`offline` events alone are not enough to trust: some browsers (notably
 * Chrome on Windows behind certain adapters/VPNs) fire a spurious one-off
 * "offline" event with no matching "offline" follow-up, permanently wedging state
 * that only ever listens for events. To self-heal from that, this also re-reads
 * `navigator.onLine` directly on window focus/visibility-return and on a slow
 * background poll — cheap, synchronous property reads, not network calls.
 */
import { useEffect, useState } from "react";

const POLL_MS = 15_000;

function readInitialOnline(): boolean {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

export function useOnlineStatus(): boolean {
  // Lazy initializer reads the real value on first client render — no setState-in-effect needed.
  const [online, setOnline] = useState(readInitialOnline);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    const resync = () => setOnline(navigator.onLine);

    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    window.addEventListener("focus", resync);
    document.addEventListener("visibilitychange", resync);
    const interval = window.setInterval(resync, POLL_MS);

    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("focus", resync);
      document.removeEventListener("visibilitychange", resync);
      window.clearInterval(interval);
    };
  }, []);

  return online;
}
