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

export type WsStatusListener = (connected: boolean) => void;

const RECONNECT_DELAYS_MS = [1000, 2000, 5000, 10000];

/**
 * Thin wrapper around a single WebSocket connection. `connect()` opens it,
 * `subscribe()` registers a message listener (returns an unsubscribe
 * function), `onStatusChange()` reports open/close transitions (used by
 * RealtimeProvider to expose LIVE vs DEMO), `disconnect()` closes it for good
 * (no further reconnect attempts).
 *
 * Reconnects with backoff (1s, 2s, 5s, 10s, then holds at 10s) on an
 * unexpected close, so a backend that starts later still gets picked up
 * without a page reload. A deliberate disconnect() never reconnects.
 */
export class OpAssureSocket {
  private socket: WebSocket | null = null;
  private listeners = new Set<WsListener>();
  private statusListeners = new Set<WsStatusListener>();
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closedByClient = false;
  private url = "";

  connect(url: string = WS_URL): void {
    if (!url) return;
    this.url = url;
    this.closedByClient = false;
    this.open();
  }

  private open(): void {
    if (!this.url) return;
    let socket: WebSocket;
    try {
      socket = new WebSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }
    socket.onmessage = (event) => {
      const message = parseWsMessage(event.data);
      if (message) this.listeners.forEach((listener) => listener(message));
    };
    socket.onopen = () => {
      this.reconnectAttempt = 0;
      this.statusListeners.forEach((listener) => listener(true));
    };
    socket.onclose = () => {
      this.statusListeners.forEach((listener) => listener(false));
      if (!this.closedByClient) this.scheduleReconnect();
    };
    socket.onerror = () => {
      socket.close();
    };
    this.socket = socket;
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    const delay = RECONNECT_DELAYS_MS[Math.min(this.reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)];
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (!this.closedByClient) this.open();
    }, delay);
  }

  subscribe(listener: WsListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Reports connection open/close transitions — the basis for a LIVE vs DEMO indicator. */
  onStatusChange(listener: WsStatusListener): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  disconnect(): void {
    this.closedByClient = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
  }

  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }
}
