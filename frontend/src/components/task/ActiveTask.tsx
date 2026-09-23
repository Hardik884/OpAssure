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
import { useActiveTaskInsight } from "@/hooks/useActiveTaskInsight";
import { useSafety } from "@/hooks/useSafety";
import { useTask } from "@/hooks/useTask";
import { api } from "@/lib/api";
import { weatherGlyph } from "@/lib/format";
import type { IncidentEventType, SafetyEvent } from "@/types";

import { Button, Card, Empty, ErrorNote, PageContainer } from "../common/ui";
import { IncidentModal } from "../safety/IncidentModal";
import { ProximityAlert } from "../safety/ProximityAlert";
import { SafetyStatus } from "../safety/SafetyStatus";

type QuickReport = { eventType: IncidentEventType; note: string };
type Overlay = { mode: "form" } | { mode: "quick"; report: QuickReport } | null;

export function ActiveTask() {
  const { context, setSafetyStatus } = useOperatorContext();
  const { task, loading, error } = useTask();
  const { insight } = useActiveTaskInsight(task?.taskId);
  const { events: safetyEvents } = useSafety();

  const [proximityAlert, setProximityAlert] = useState<SafetyEvent | null>(null);
  const [overlay, setOverlay] = useState<Overlay>(null);

  const simulateProximityAlert = () => {
    api.triggerDemoProximityAlert().then((alert) => {
      setProximityAlert(alert);
      setSafetyStatus(alert.severity);
    });
  };

  const clearProximityAlert = () => {
    setProximityAlert(null);
    setSafetyStatus("safe");
  };

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

  const behindPlan = task.etaMax - task.originalEta;
  // The persistent Safety strip must never contradict the override banner above it —
  // while a demo/live proximity alert is active, it replaces the ambient "proximity" row.
  const displayedSafetyEvents = proximityAlert
    ? [...safetyEvents.filter((e) => e.event !== "proximity"), proximityAlert]
    : safetyEvents;

  return (
    <PageContainer>
      <p className="text-xs font-bold uppercase tracking-widest text-line-500">Active Task · {task.taskId}</p>
      <h1 className="text-3xl font-black uppercase tracking-tight text-ink-950 sm:text-4xl">{task.taskType}</h1>
      <p className="mb-4 text-sm font-bold uppercase tracking-wide text-line-600">Zone {task.zone}</p>

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
              {task.etaMin === task.etaMax ? task.etaMin : `${task.etaMin}–${task.etaMax}`}
              <span className="ml-2 text-xl font-bold text-line-400">min</span>
            </div>
            <p className="mt-2 text-sm font-semibold text-line-400">Original {task.originalEta} min</p>

            {insight && insight.etaReasons.length > 0 && (
              <details className="mt-4 border-t border-ink-800 pt-3">
                <summary className="cursor-pointer text-sm font-black uppercase tracking-wide text-brand-500">
                  Why?
                </summary>
                <ul className="mt-2 space-y-1 pl-1 text-sm text-line-300">
                  {insight.etaReasons.map((reason) => (
                    <li key={reason}>• {reason}</li>
                  ))}
                </ul>
              </details>
            )}
          </Card>

          {/* Progress */}
          <Card rounded="lg">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-ink-600">Buckets remaining</p>
                <p className="text-5xl font-black tabular-nums leading-none text-ink-950">{task.bucketsRemaining}</p>
              </div>
              <div className="text-right">
                {insight && <p className="text-sm font-semibold text-line-600">Approx. {insight.approxTrucksRemaining} trucks</p>}
                <p className="text-sm font-semibold text-line-600">
                  {weatherGlyph(task.weather)} {task.weather}
                </p>
              </div>
            </div>
          </Card>

          {/* Actions */}
          <Card rounded="lg">
            <p className="mb-3 text-xs font-bold uppercase tracking-widest text-ink-600">Report</p>
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
            <p className="mb-1 text-xs font-bold uppercase tracking-widest text-ink-600">Demo control</p>
            <p className="mb-3 text-xs font-medium text-line-500">Stands in for the live WebSocket feed for now.</p>
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
