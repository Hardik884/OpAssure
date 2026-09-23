/**
 * The single place the frontend talks to the backend (CLAUDE.md: no fetch calls
 * scattered through components). Every screen/hook goes through the `api` object
 * below, never `fetch` directly.
 *
 * Mock vs real: `USE_MOCK_DATA` (config/env.ts) picks the source. Every function
 * has the same async signature either way, so flipping the flag later — once
 * Mission Board/Active Task/Safety are built — is a one-line change per function,
 * not a rewrite of the callers.
 *
 * When wiring the real backend (see docs/api/README.md), map its snake_case
 * response fields onto the frozen types in ../types HERE, at the boundary —
 * never rename fields inside components (CLAUDE.md §10).
 */
import { API_URL, USE_MOCK_DATA } from "@/config/env";
import {
  mockActiveTaskInsightByTask, mockCriticalProximityAlert, mockMissionTasks, mockOperatorContext,
  mockOperatorInsight, mockSafetyEvents, mockTask, mockThreatBriefingByTask,
} from "@/lib/mockData";
import type {
  ActiveTaskInsight, Incident, IncidentInput, MissionTask, OperatorContext, OperatorInsight, SafetyEvent, Task,
  ThreatBriefingItem,
} from "@/types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** Generic JSON fetch helper for the real backend. Not yet used by any endpoint below. */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_URL) throw new ApiError(0, "NEXT_PUBLIC_API_URL is not set");
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError(0, "Backend unreachable");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.message ?? `Request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

/** Simulates async network latency so loading states behave the same as real calls. */
function mockResolve<T>(value: T, delayMs = 150): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), delayMs));
}

export const api = {
  /** Operator, machine, current task and overall safety status in one shape. */
  getOperatorContext(): Promise<OperatorContext> {
    if (USE_MOCK_DATA) return mockResolve(mockOperatorContext);
    // TODO(real API): assemble from GET /operators/{id}, /machines/{id}, /tasks/today.
    return request<OperatorContext>("/operator-context");
  },

  getCurrentTask(): Promise<Task> {
    if (USE_MOCK_DATA) return mockResolve(mockTask);
    // TODO(real API): GET /tasks/{id}; map snake_case fields to Task here.
    return request<Task>("/tasks/current");
  },

  getSafetyEvents(): Promise<SafetyEvent[]> {
    if (USE_MOCK_DATA) return mockResolve(mockSafetyEvents);
    // TODO(real API): GET /safety/{machine_id}; map `alerts[]` to SafetyEvent[] here.
    return request<SafetyEvent[]>("/safety/events");
  },

  getOperatorInsight(): Promise<OperatorInsight> {
    if (USE_MOCK_DATA) return mockResolve(mockOperatorInsight);
    // TODO(real API): GET /operator/{id}/insights; map to OperatorInsight here.
    return request<OperatorInsight>("/operator/insight");
  },

  /** Mission Board rows for today, in schedule order. */
  getTodayTasks(): Promise<MissionTask[]> {
    if (USE_MOCK_DATA) return mockResolve(mockMissionTasks);
    // TODO(real API): GET /tasks/today?operator_id=OP1001; map snake_case fields
    // (task_id, task_type, estimated_time_min, start_time, ...) to MissionTask here.
    return request<MissionTask[]>("/tasks/today");
  },

  /** A single task by id (Mission Board's "VIEW" action). */
  getTask(taskId: string): Promise<Task | undefined> {
    if (USE_MOCK_DATA) return mockResolve(mockMissionTasks.find((t) => t.taskId === taskId));
    // TODO(real API): GET /tasks/{id}; map fields to Task here.
    return request<Task>(`/tasks/${taskId}`);
  },

  /** Pre-Task Threat Briefing facts for a task (empty if there's nothing to brief). */
  getThreatBriefing(taskId: string): Promise<ThreatBriefingItem[]> {
    if (USE_MOCK_DATA) return mockResolve(mockThreatBriefingByTask[taskId] ?? []);
    // TODO(real API): once the backend exposes a briefing endpoint, map it here.
    return request<ThreatBriefingItem[]>(`/tasks/${taskId}/threat-briefing`);
  },

  /** Supplementary Active Task facts (ETA reasons, truck estimate). */
  getActiveTaskInsight(taskId: string): Promise<ActiveTaskInsight | null> {
    if (USE_MOCK_DATA) return mockResolve(mockActiveTaskInsightByTask[taskId] ?? null);
    // TODO(real API): derive from GET /ml-input/operator/{id} (eta_update reason, etc.).
    return request<ActiveTaskInsight>(`/tasks/${taskId}/insight`);
  },

  /** Records an operator-reported incident. Always returns a telemetry-attached record. */
  recordIncident(input: IncidentInput): Promise<Incident> {
    if (USE_MOCK_DATA) {
      const incident: Incident = {
        ...input,
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
        hasTelemetryContext: true,
      };
      return mockResolve(incident);
    }
    // TODO(real API): POST /incidents with { operator_id, machine_id, task_id, type: eventType,
    // description: note }; map the { snapshot_size, telemetry_snapshot } response back here.
    return request<Incident>("/incidents", { method: "POST", body: JSON.stringify(input) });
  },

  /**
   * Demo-only: stands in for a live WS `proximity_alert` event until realtime
   * integration lands. Returns the frozen critical example every time.
   */
  triggerDemoProximityAlert(): Promise<SafetyEvent> {
    return mockResolve(mockCriticalProximityAlert, 50);
  },
};

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong";
}
