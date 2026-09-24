"use client";

/**
 * Honest offline state: the browser itself has no network. Distinct from the
 * WebSocket's "demo mode" (RealtimeProvider) — this is a real connectivity
 * signal, shown once, app-wide, never a synthesized "live" value.
 *
 * `navigator.onLine`/the online-offline events are unreliable in practice
 * (known to misreport on Windows behind certain adapters/VPNs, and once it
 * flips false there's often no follow-up "online" event to correct it). A
 * successfully connected live WebSocket is strictly stronger proof of
 * connectivity than that browser flag, so it overrides a stale "offline"
 * reading here rather than leaving the banner stuck showing offline while
 * the app is demonstrably talking to the backend.
 */
import { AlertTriangleIcon } from "@/components/common/icons";
import { useRealtime } from "@/components/layout/RealtimeProvider";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";

export function OfflineBanner() {
  const browserOnline = useOnlineStatus();
  const { connectionMode } = useRealtime();
  const online = browserOnline || connectionMode === "live";

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
