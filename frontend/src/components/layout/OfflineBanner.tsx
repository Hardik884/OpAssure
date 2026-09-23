"use client";

/**
 * Honest offline state: the browser itself has no network. Distinct from the
 * WebSocket's "demo mode" (RealtimeProvider) — this is a real connectivity
 * signal, shown once, app-wide, never a synthesized "live" value.
 */
import { useOnlineStatus } from "@/hooks/useOnlineStatus";

export function OfflineBanner() {
  const online = useOnlineStatus();

  // Always render the same element (server and client) — only its visibility differs — so a
  // stored offline state at hydration time never produces a structural hydration mismatch.
  return (
    <div
      role="status"
      suppressHydrationWarning
      className={
        online
          ? "hidden"
          : "border-b-2 border-warn-600 bg-warn-500 px-4 py-2 text-center text-sm font-bold uppercase tracking-wide text-ink-950"
      }
    >
      ⚠ Offline — showing last-known data. Read-only until reconnected.
    </div>
  );
}
