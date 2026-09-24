/**
 * Critical proximity override banner, built directly from the frozen
 * SafetyEvent contract. Renders nothing when there's no active alert, so it
 * costs no layout space until it's needed — and nothing to rewrite when a
 * later WS `proximity_alert` event replaces the demo trigger that feeds it.
 */
import { AlertOctagonIcon } from "@/components/common/icons";
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
    ? "border-critical-500/30 bg-critical-500 text-white"
    : "border-warn-500/30 bg-warn-500 text-ink-950";
  const ringColor = critical ? "border-white/70" : "border-ink-950/50";

  return (
    <div role="alert" data-testid="proximity-alert" className={`animate-rise-in mb-4 rounded-panel border p-4 sm:p-5 ${tone}`}>
      <div className="flex items-start gap-4">
        <div className="relative flex h-11 w-11 shrink-0 items-center justify-center">
          <span className={`absolute inset-0 rounded-full border-2 ${ringColor} animate-radar-ping`} aria-hidden />
          <span className="relative flex h-11 w-11 items-center justify-center rounded-full bg-black/10">
            <AlertOctagonIcon className="h-6 w-6" aria-hidden />
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] opacity-90">Proximity Alert</div>
          <div className="mt-0.5 font-display text-xl font-semibold tracking-tight sm:text-2xl">Worker detected</div>

          <div className="mt-2 flex items-baseline gap-3">
            <span className="font-display text-5xl font-semibold tabular-nums leading-none">{alert.distance ?? "–"}</span>
            <span className="text-lg font-semibold">m</span>
            {alert.direction && <span className="text-sm font-semibold uppercase tracking-wide opacity-90">{alert.direction}</span>}
          </div>

          <p className="mt-2 text-sm font-medium opacity-95">{alert.message}</p>
          {machineMoving && (
            <p className="mt-1 text-xs font-semibold uppercase tracking-[0.1em] opacity-75">Machine moving</p>
          )}
        </div>
      </div>
    </div>
  );
}
