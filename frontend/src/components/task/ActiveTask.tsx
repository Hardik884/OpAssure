"use client";

/**
 * The Active Task screen — designed so an operator understands the situation
 * in about one second. Visual hierarchy: critical alerts override everything,
 * then the current ETA (the dominant number), then progress, then context,
 * then actions. The frontend renders etaMin/etaMax/originalEta exactly as
 * given — it never calculates an ETA itself.
 */
import { useState } from "react";

import { useOperatorContext } from "@/components/layout/OperatorProvider";
import { useRealtime } from "@/components/layout/RealtimeProvider";
import { useActiveTaskInsight } from "@/hooks/useActiveTaskInsight";
import { useSafety } from "@/hooks/useSafety";
import { useTask } from "@/hooks/useTask";
import { useTrainingRecommendation } from "@/hooks/useTrainingRecommendation";
import { api } from "@/lib/api";
import { weatherGlyph } from "@/lib/format";
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
      <p className="text-xs font-bold uppercase tracking-widest text-foreground-muted">Active Task · {task.taskId}</p>
      <h1 className="text-3xl font-black uppercase tracking-tight text-foreground sm:text-4xl">{task.taskType}</h1>
      <p className="mb-4 text-sm font-bold uppercase tracking-wide text-foreground-muted">Zone {task.zone}</p>

      <ProximityAlert alert={proximityAlert} />

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-4">
          {/* Current ETA — the dominant number on the screen. */}
          <Card rounded="lg" tone="dark">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold uppercase tracking-widest text-line-400">Current ETA</p>
              {behindPlan >= 3 && (
                <span className="rounded-industrial bg-warn-500 px-2 py-1 text-xs font-black uppercase tracking-wide text-ink-950">
                  +{behindPlan} min
                </span>
              )}
            </div>
            <div className="text-6xl font-black tabular-nums leading-none sm:text-7xl">
              {etaMin === etaMax ? etaMin : `${etaMin}–${etaMax}`}
              <span className="ml-2 text-xl font-bold text-line-400">min</span>
            </div>
            <p className="mt-2 text-sm font-semibold text-line-400">Original {originalEta} min</p>

            {etaReasons.length > 0 && (
              <details className="mt-4 border-t border-ink-800 pt-3">
                <summary className="cursor-pointer text-sm font-black uppercase tracking-wide text-brand-500">
                  Why?
                </summary>
                <ul className="mt-2 space-y-1 pl-1 text-sm text-line-300">
                  {etaReasons.map((reason) => (
                    <li key={reason}>• {reason}</li>
                  ))}
                </ul>
              </details>
            )}
          </Card>

          {trainingRecommendation && <TrainingRecommendationCard recommendation={trainingRecommendation} />}

          {/* Progress */}
          <Card rounded="lg">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-foreground-muted">Buckets remaining</p>
                <p className="text-5xl font-black tabular-nums leading-none text-foreground">{task.bucketsRemaining}</p>
              </div>
              <div className="text-right">
                {insight && <p className="text-sm font-semibold text-foreground-muted">Approx. {insight.approxTrucksRemaining} trucks</p>}
                <p className="text-sm font-semibold text-foreground-muted">
                  {weatherGlyph(task.weather)} {task.weather}
                </p>
              </div>
            </div>
          </Card>

          {/* Actions */}
          <Card rounded="lg">
            <p className="mb-3 text-xs font-bold uppercase tracking-widest text-foreground-muted">Report</p>
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
              <p className="text-xs font-bold uppercase tracking-widest text-foreground-muted">Real-time feed</p>
              <StatusDot
                status={realtime.connectionMode === "live" ? "safe" : "warning"}
                label={realtime.connectionMode === "live" ? "Live" : "Demo mode"}
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
