"use client";

/**
 * Honest offline state: the browser itself has no network. Distinct from the
 * WebSocket's "demo mode" (RealtimeProvider) — this is a real connectivity
 * signal, shown once, app-wide, never a synthesized "live" value.
 */
import { AlertTriangleIcon } from "@/components/common/icons";
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
          : "flex items-center justify-center gap-2 border-b border-warn-600/40 bg-warn-500 px-4 py-2 text-center text-sm font-semibold text-ink-950"
      }
    >
      <AlertTriangleIcon className="h-4 w-4 shrink-0" aria-hidden />
      Offline — showing last-known data. Read-only until reconnected.
    </div>
  );
}
