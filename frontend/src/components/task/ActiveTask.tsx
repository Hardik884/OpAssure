"use client";

/**
 * The Active Task screen — designed so an operator understands the situation
 * in about one second. Visual hierarchy: critical alerts override everything,
 * then the current ETA (the dominant number), then progress, then context,
 * then actions. The frontend renders etaMin/etaMax/originalEta exactly as
 * given — it never calculates an ETA itself.
 */
import { useState } from "react";

import { ClockIcon, FuelIcon, GaugeIcon } from "@/components/common/icons";
import { useOperatorContext } from "@/components/layout/OperatorProvider";
import { useRealtime } from "@/components/layout/RealtimeProvider";
import { useActiveTaskInsight } from "@/hooks/useActiveTaskInsight";
import { useSafety } from "@/hooks/useSafety";
import { useTask } from "@/hooks/useTask";
import { useTelemetry } from "@/hooks/useTelemetry";
import { useTrainingRecommendation } from "@/hooks/useTrainingRecommendation";
import { api } from "@/lib/api";
import { DEFAULT_WEATHER_ICON, WEATHER_ICON } from "@/lib/format";
import type { IncidentEventType, SafetyEvent } from "@/types";

import { Button, Card, Empty, ErrorNote, PageContainer, StatusDot } from "../common/ui";
import { IncidentModal } from "../safety/IncidentModal";
import { ProximityAlert } from "../safety/ProximityAlert";
import { SafetyStatus } from "../safety/SafetyStatus";
import { TrainingRecommendationCard } from "../training/TrainingRecommendationCard";

type QuickReport = { eventType: IncidentEventType; note: string };
type Overlay = { mode: "form" } | { mode: "quick"; report: QuickReport } | null;

export function ActiveTask() {
  const { context, setSafetyStatus } = useOperatorContext();
  const { task, loading, error } = useTask();
  const { insight } = useActiveTaskInsight(task?.taskId);
  const { events: safetyEvents } = useSafety();
  const { telemetry } = useTelemetry();
  const realtime = useRealtime();
  const { recommendation: trainingRecommendation } = useTrainingRecommendation();

  const [demoProximityAlert, setDemoProximityAlert] = useState<SafetyEvent | null>(null);
  const [overlay, setOverlay] = useState<Overlay>(null);

  const simulateProximityAlert = () => {
    api.triggerDemoProximityAlert().then((alert) => {
      setDemoProximityAlert(alert);
      setSafetyStatus(alert.severity);
    });
  };

  const clearProximityAlert = () => {
    setDemoProximityAlert(null);
    setSafetyStatus("safe");
  };

  // A live/real WS proximity_alert always wins over the local demo trigger — the
  // demo control exists only for when no backend is connected (see connectionMode below).
  const proximityAlert: SafetyEvent | null = realtime.proximityAlert
    ? {
        event: "proximity_alert",
        severity: realtime.proximityAlert.severity,
        distance: realtime.proximityAlert.distance,
        direction: realtime.proximityAlert.direction,
        message: `Worker detected ${realtime.proximityAlert.direction}`,
      }
    : demoProximityAlert;

  if (error) {
    return (
      <PageContainer>
        <ErrorNote>{error}</ErrorNote>
      </PageContainer>
    );
  }

  if (loading || !task) {
    return (
      <PageContainer>
        <Card>
          <Empty>Loading active task…</Empty>
        </Card>
      </PageContainer>
    );
  }

  // A live eta_update overrides the plan's static min/max/original — the frontend still
  // never computes an ETA itself, only renders whichever source (live or planned) applies.
  const etaMin = realtime.etaUpdate?.min ?? task.etaMin;
  const etaMax = realtime.etaUpdate?.max ?? task.etaMax;
  const originalEta = realtime.etaUpdate?.original ?? task.originalEta;
  const etaReasons = realtime.etaUpdate ? [realtime.etaUpdate.reason] : insight?.etaReasons ?? [];
  const behindPlan = etaMax - originalEta;
  const onTrack = behindPlan < 3;
  const WeatherIcon = WEATHER_ICON[task.weather.trim().toLowerCase()] ?? DEFAULT_WEATHER_ICON;

  // The persistent Safety strip must never contradict the override banner above it —
  // while a demo/live proximity or safety alert is active, it replaces the matching ambient row.
  let displayedSafetyEvents = safetyEvents;
  if (proximityAlert) {
    displayedSafetyEvents = [...displayedSafetyEvents.filter((e) => !e.event.startsWith("proximity")), proximityAlert];
  }
  if (realtime.safetyAlert) {
    const liveSafetyEvent: SafetyEvent = {
      event: realtime.safetyAlert.type,
      severity: realtime.safetyAlert.severity,
      distance: null,
      direction: null,
      message: realtime.safetyAlert.message,
    };
    displayedSafetyEvents = [
      ...displayedSafetyEvents.filter((e) => !e.event.startsWith(realtime.safetyAlert!.type)),
      liveSafetyEvent,
    ];
  }

  return (
    <PageContainer>
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-foreground-muted">Active Task · {task.taskId}</p>
      <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">{task.taskType}</h1>
      <p className="mb-4 text-sm font-medium text-foreground-muted">Zone {task.zone}</p>

      <ProximityAlert alert={proximityAlert} />

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-4">
          {/* Current ETA — the dominant number on the screen, framed in a status ring. */}
          <Card rounded="lg" tone="dark">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-line-400">Current ETA</p>
              {behindPlan >= 3 && (
                <span className="rounded-full bg-warn-500 px-2.5 py-1 text-xs font-semibold text-ink-950">
                  +{behindPlan} min behind plan
                </span>
              )}
            </div>

            <div className="mt-4 flex flex-col items-center gap-1 py-2 sm:flex-row sm:items-center sm:justify-center sm:gap-8">
              <div className="relative flex h-40 w-40 shrink-0 items-center justify-center">
                <svg width="160" height="160" viewBox="0 0 160 160" className={onTrack ? "animate-soft-glow" : ""}>
                  <circle cx="80" cy="80" r="70" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    fill="none"
                    stroke={onTrack ? "var(--color-teal-500)" : "var(--color-warn-500)"}
                    strokeWidth="10"
                    strokeLinecap="round"
                    strokeDasharray="440"
                    strokeDashoffset="18"
                    transform="rotate(-90 80 80)"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="font-display text-4xl font-semibold tabular-nums leading-none text-white">
                    {etaMin === etaMax ? etaMin : `${etaMin}–${etaMax}`}
                  </span>
                  <span className="mt-1 text-xs font-medium text-line-400">min remaining</span>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2 sm:items-start">
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ${
                    onTrack ? "bg-teal-500/15 text-teal-400" : "bg-warn-500/15 text-brand-400"
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${onTrack ? "bg-teal-400" : "bg-brand-400"}`} aria-hidden />
                  {onTrack ? "On track" : "Running behind"}
                </span>
                <p className="text-sm font-medium text-line-400">Original {originalEta} min</p>
              </div>
            </div>

            {etaReasons.length > 0 && (
              <details className="mt-4 border-t border-white/10 pt-3">
                <summary className="cursor-pointer text-sm font-semibold text-brand-500">Why?</summary>
                <ul className="mt-2 space-y-1 pl-1 text-sm text-line-300">
                  {etaReasons.map((reason) => (
                    <li key={reason}>· {reason}</li>
                  ))}
                </ul>
              </details>
            )}
          </Card>

          {trainingRecommendation && <TrainingRecommendationCard recommendation={trainingRecommendation} />}

          {/* Live telemetry — only rendered once a real feed supplies it; never a placeholder number. */}
          {telemetry && (
            <div className="grid grid-cols-3 gap-3">
              <TelemetryTile icon={FuelIcon} label="Fuel used" value={`${telemetry.fuel}L`} />
              <TelemetryTile icon={GaugeIcon} label="Avg cycle" value={telemetry.cycleTime ? `${telemetry.cycleTime}s` : "–"} />
              <TelemetryTile icon={ClockIcon} label="Idle time" value={`${telemetry.idle}m`} />
            </div>
          )}

          {/* Progress */}
          <Card rounded="lg">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">Buckets remaining</p>
                <p className="font-display text-5xl font-semibold tabular-nums leading-none text-foreground">{task.bucketsRemaining}</p>
              </div>
              <div className="text-right">
                {insight && <p className="text-sm font-medium text-foreground-muted">Approx. {insight.approxTrucksRemaining} trucks</p>}
                <p className="flex items-center justify-end gap-1.5 text-sm font-medium text-foreground-muted">
                  <WeatherIcon className="h-4 w-4 shrink-0" aria-hidden />
                  {task.weather}
                </p>
              </div>
            </div>
          </Card>

          {/* Actions */}
          <Card rounded="lg">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">Report</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Button
                variant="secondary"
                onClick={() => setOverlay({ mode: "quick", report: { eventType: "ground", note: "Hit rock encountered" } })}
              >
                Hit Rock
              </Button>
              <Button
                variant="secondary"
                onClick={() => setOverlay({ mode: "quick", report: { eventType: "ground", note: "Ground reported wet" } })}
              >
                Ground Wet
              </Button>
              <Button variant="primary" onClick={() => setOverlay({ mode: "form" })}>
                Report Issue
              </Button>
            </div>
          </Card>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-36 lg:h-fit">
          <SafetyStatus events={displayedSafetyEvents} />

          <Card>
            <div className="mb-1 flex items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">Real-time feed</p>
              <StatusDot
                status={realtime.connectionMode === "live" ? "safe" : "warning"}
                label={realtime.connectionMode === "live" ? "Live" : "Demo mode"}
                pulse={realtime.connectionMode === "live"}
              />
            </div>
            <p className="mb-3 text-xs font-medium text-foreground-muted">
              {realtime.connectionMode === "live"
                ? "Connected to the live backend feed."
                : "Real-time offline — using the local demo control below."}
            </p>
            {proximityAlert ? (
              <Button variant="ghost" className="w-full" onClick={clearProximityAlert}>
                Mark Area Clear
              </Button>
            ) : (
              <Button variant="ghost" className="w-full" onClick={simulateProximityAlert}>
                Simulate Proximity Alert
              </Button>
            )}
          </Card>
        </aside>
      </div>

      {overlay && (
        <IncidentModal
          operatorId={context.operator.operatorId}
          machineId={context.machine.machineId}
          taskId={task.taskId}
          quickReport={overlay.mode === "quick" ? overlay.report : undefined}
          onClose={() => setOverlay(null)}
        />
      )}
    </PageContainer>
  );
}

function TelemetryTile({ icon: Icon, label, value }: { icon: typeof FuelIcon; label: string; value: string }) {
  return (
    <Card className="flex flex-col gap-1.5">
      <Icon className="h-4 w-4 text-brand-500" aria-hidden />
      <span className="font-display text-lg font-semibold tabular-nums text-foreground">{value}</span>
      <span className="text-xs font-medium text-foreground-muted">{label}</span>
    </Card>
  );
}
