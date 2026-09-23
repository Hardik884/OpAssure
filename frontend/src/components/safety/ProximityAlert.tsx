/**
 * Critical proximity override banner, built directly from the frozen
 * SafetyEvent contract. Renders nothing when there's no active alert, so it
 * costs no layout space until it's needed — and nothing to rewrite when a
 * later WS `proximity_alert` event replaces the demo trigger that feeds it.
 */
import type { SafetyEvent } from "@/types";

interface ProximityAlertProps {
  alert: SafetyEvent | null;
  /** Mirrors the real telemetry_update.movement field — shown as context, not computed here. */
  machineMoving?: boolean;
}

export function ProximityAlert({ alert, machineMoving = true }: ProximityAlertProps) {
  if (!alert) return null;

  const critical = alert.severity === "critical";
  const tone = critical
    ? "animate-pulse border-critical-600 bg-critical-500 text-white"
    : "border-warn-600 bg-warn-500 text-ink-950";

  return (
    <div role="alert" data-testid="proximity-alert" className={`mb-4 rounded-panel border-2 p-4 ${tone}`}>
      <div className="flex items-center gap-2 text-sm font-black uppercase tracking-widest">
        <span aria-hidden>⛔</span>
        Proximity Alert
      </div>
      <div className="mt-1 text-2xl font-black uppercase tracking-tight">Worker Detected</div>
      <div className="mt-1 flex items-baseline gap-3">
        <span className="text-5xl font-black tabular-nums leading-none">{alert.distance ?? "–"}</span>
        <span className="text-lg font-bold">m</span>
        {alert.direction && <span className="text-lg font-black uppercase tracking-wide">{alert.direction}</span>}
      </div>
      <p className="mt-2 text-sm font-semibold">{alert.message}</p>
      {machineMoving && (
        <p className="mt-1 text-xs font-bold uppercase tracking-widest opacity-90">Machine moving</p>
      )}
    </div>
  );
}
