"use client";

/**
 * Placeholder for live telemetry (WS /ws `telemetry_update`). This foundation
 * prompt establishes the hook's shape only; Prompt 2+ wires it to
 * lib/websocket.ts once Active Task needs a live feed.
 */
import { useState } from "react";

export interface TelemetrySnapshot {
  cycleTime: number | null;
  idle: number;
  fuel: number;
  belt: string;
  movement: boolean;
}

interface UseTelemetryResult {
  telemetry: TelemetrySnapshot | null;
  connected: boolean;
}

export function useTelemetry(): UseTelemetryResult {
  // No live subscription yet — returns an empty snapshot so consumers can render
  // their "no data yet" state without special-casing this hook.
  const [telemetry] = useState<TelemetrySnapshot | null>(null);
  return { telemetry, connected: false };
}
