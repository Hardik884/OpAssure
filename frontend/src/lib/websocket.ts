/**
 * WebSocket abstraction — event typing + a minimal connection wrapper.
 *
 * Scope for this foundation prompt: the message contract and a bare-bones client
 * good enough for a later hook to subscribe to. Reconnection strategy, event
 * de-duplication, and driving the live dashboard are explicitly later work
 * ("advanced WebSocket behavior" is out of scope here) — see the realtime hooks
 * (useTelemetry/useSafety/useTask) for where that will plug in.
 *
 * Wire format matches the backend (`docs/api/README.md`):
 *   {"event": "telemetry_update", "version": 1, "data": {...}}
 */
import { WS_URL } from "@/config/env";

export type WsEventName =
  | "telemetry_update"
  | "safety_alert"
  | "proximity_alert"
  | "eta_update"
  | "habit_detected"
  | "training_recommendation"
  | "replay_status"
  | "error"
  | "pong";

export interface WsMessage<TData = unknown> {
  event: WsEventName;
  version: number;
  data: TData;
}

export type WsListener = (message: WsMessage) => void;

/** Type guard + minimal parse for one raw WebSocket frame. Malformed frames are dropped. */
export function parseWsMessage(raw: unknown): WsMessage | null {
  if (typeof raw !== "string") return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.event === "string" && parsed.data && typeof parsed.data === "object") {
      return parsed as WsMessage;
    }
  } catch {
    // fall through
  }
  return null;
}

/**
 * Thin wrapper around a single WebSocket connection. `connect()` opens it,
 * `subscribe()` registers a listener (returns an unsubscribe function),
 * `disconnect()` closes it. No auto-reconnect yet — a later prompt owns that.
 */
export class OpAssureSocket {
  private socket: WebSocket | null = null;
  private listeners = new Set<WsListener>();

  connect(url: string = WS_URL): void {
    if (!url || this.socket) return;
    const socket = new WebSocket(url);
    socket.onmessage = (event) => {
      const message = parseWsMessage(event.data);
      if (message) this.listeners.forEach((listener) => listener(message));
    };
    this.socket = socket;
  }

  subscribe(listener: WsListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  disconnect(): void {
    this.socket?.close();
    this.socket = null;
  }

  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }
}
