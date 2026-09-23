/**
 * Shared frontend types.
 *
 * Two layers, deliberately kept separate:
 *   1. Domain contract types below (Task, SafetyEvent, OperatorInsight, ...) — these
 *      field names are FROZEN by the OpAssure Frontend Handover and MUST NOT be
 *      silently renamed. Prompt 2+ (Mission Board, Active Task, ...) builds against
 *      these shapes using mock data first, then real API data later, without a
 *      rewrite either time.
 *   2. `OperatorContext` / status enums — small reusable shapes the app shell needs
 *      right now (header, nav, layout).
 *
 * The real backend's REST contracts (snake_case, documented in docs/api/README.md)
 * are intentionally NOT modeled here yet. Wiring lib/api.ts to the real backend is
 * later work; when it happens the mapping happens at the API boundary (lib/api.ts),
 * never by renaming these fields (see CLAUDE.md §10 — no silent renames).
 */

/** green = normal/safe, amber = attention required, red = immediate operator action. */
export type RiskLevel = "low" | "medium" | "high";

/** Overall machine/operator safety posture shown in the header and safety views. */
export type SafetyStatus = "safe" | "warning" | "critical";

export type Direction = "front" | "right" | "rear" | "left";

/**
 * A scheduled or active unit of work for an operator on a machine.
 * Field names are frozen by the handover — do not rename.
 */
export interface Task {
  taskId: string;
  taskType: string;
  zone: string;
  originalEta: number;
  etaMin: number;
  etaMax: number;
  bucketsRemaining: number;
  weather: string;
  riskLevel: RiskLevel;
}

/**
 * A live safety occurrence (seatbelt, proximity, idle, ...). Field names are
 * frozen by the handover — do not rename.
 */
export interface SafetyEvent {
  event: string;
  severity: SafetyStatus;
  distance: number | null;
  direction: Direction | null;
  message: string;
}

/**
 * Operator Twin summary: how this operator tends to work. Field names are frozen
 * by the handover — do not rename.
 */
export interface OperatorInsight {
  operatorId: string;
  paceFactor: number;
  rainSensitivity: number;
  fatiguePattern: string;
  riskLevel: RiskLevel;
}

/** Static identity — who is in the cab and what they're driving. */
export interface Operator {
  operatorId: string;
  name: string;
  skill: string;
}

export interface Machine {
  machineId: string;
  type: string;
  model: string;
}

/**
 * The one place "who / what / which task / how safe" is assembled for the rest of
 * the app to read. Populated from mock data today; from the backend later — the
 * shape does not need to change when that happens.
 */
export interface OperatorContext {
  operator: Operator;
  machine: Machine;
  currentTask: Task | null;
  safetyStatus: SafetyStatus;
}

/** Primary navigation destinations for the operator shell. */
export type NavKey = "mission" | "task" | "safety" | "training" | "insights" | "history";
