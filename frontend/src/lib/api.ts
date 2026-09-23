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
import { mockOperatorContext, mockOperatorInsight, mockSafetyEvents, mockTask } from "@/lib/mockData";
import type { OperatorContext, OperatorInsight, SafetyEvent, Task } from "@/types";

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
};

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong";
}
