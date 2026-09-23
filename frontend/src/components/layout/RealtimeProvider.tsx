"use client";

/**
 * The single centralized realtime connection for the whole app (CLAUDE.md /
 * handover: no per-component WebSocket connections, no duplicated event
 * parsing). Wraps the one OpAssureSocket instance (lib/websocket.ts) in a
 * React context and exposes typed, per-event-type state slices.
 *
 * `connectionMode` is explicit and always accurate: "live" only while the
 * socket is actually open; "demo" otherwise (no WS_URL configured, or the
 * backend is unreachable). Consumers must use this to label real-time UI —
 * never present mock/demo data as live.
 */
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { WS_URL } from "@/config/env";
import { OpAssureSocket, type WsMessage } from "@/lib/websocket";
import type { ConnectionMode, Direction, SafetyStatus } from "@/types";

interface TelemetryUpdateData {
  machineId: string;
  operatorId: string;
  taskId: string;
  timestamp: string;
  cycleTime: number | null;
  idle: number;
  fuel: number;
  belt: string;
  movement: boolean;
}

interface SafetyAlertData {
  machineId: string;
  operatorId: string;
  taskId: string;
  timestamp: string;
  severity: SafetyStatus;
  type: string;
  message: string;
}

interface ProximityAlertData {
  machineId: string;
  timestamp: string;
  workerId: string;
  severity: SafetyStatus;
  zone: "safe" | "caution" | "critical";
  distance: number;
  direction: Direction;
}

interface EtaUpdateData {
  taskId: string;
  timestamp: string;
  min: number;
  max: number;
  original: number;
  reason: string;
  bucketsRemaining: number;
}

interface HabitDetectedData {
  operatorId: string;
  timestamp: string;
  habitType: string;
  count: number;
  explanation: string;
}

interface TrainingRecommendationData {
  operatorId: string;
  timestamp: string;
  clipId: string;
  title: string;
  reason: string;
}

interface RealtimeState {
  connectionMode: ConnectionMode;
  telemetry: TelemetryUpdateData | null;
  safetyAlert: SafetyAlertData | null;
  proximityAlert: ProximityAlertData | null;
  etaUpdate: EtaUpdateData | null;
  habitDetected: HabitDetectedData | null;
  trainingRecommendation: TrainingRecommendationData | null;
}

const INITIAL_STATE: RealtimeState = {
  connectionMode: "demo",
  telemetry: null,
  safetyAlert: null,
  proximityAlert: null,
  etaUpdate: null,
  habitDetected: null,
  trainingRecommendation: null,
};

const Context = createContext<RealtimeState | null>(null);

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<RealtimeState>(INITIAL_STATE);
  const socketRef = useRef<OpAssureSocket | null>(null);

  useEffect(() => {
    const socket = new OpAssureSocket();
    socketRef.current = socket;

    const unsubscribeStatus = socket.onStatusChange((connected) => {
      setState((prev) => ({ ...prev, connectionMode: connected ? "live" : "demo" }));
    });

    const unsubscribeMessages = socket.subscribe((message: WsMessage) => {
      switch (message.event) {
        case "telemetry_update":
          setState((prev) => ({ ...prev, telemetry: message.data as TelemetryUpdateData }));
          break;
        case "safety_alert":
          setState((prev) => ({ ...prev, safetyAlert: message.data as SafetyAlertData }));
          break;
        case "proximity_alert":
          setState((prev) => ({ ...prev, proximityAlert: message.data as ProximityAlertData }));
          break;
        case "eta_update":
          setState((prev) => ({ ...prev, etaUpdate: message.data as EtaUpdateData }));
          break;
        case "habit_detected":
          setState((prev) => ({ ...prev, habitDetected: message.data as HabitDetectedData }));
          break;
        case "training_recommendation":
          setState((prev) => ({ ...prev, trainingRecommendation: message.data as TrainingRecommendationData }));
          break;
        default:
          break;
      }
    });

    if (WS_URL) socket.connect(WS_URL);

    return () => {
      unsubscribeStatus();
      unsubscribeMessages();
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  return <Context.Provider value={state}>{children}</Context.Provider>;
}

export function useRealtime(): RealtimeState {
  const value = useContext(Context);
  if (!value) throw new Error("useRealtime must be used within RealtimeProvider");
  return value;
}
