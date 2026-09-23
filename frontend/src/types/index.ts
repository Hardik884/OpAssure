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

/* ================================================================
 * Mission Board / Active Task / Incident types (Prompt 2)
 *
 * These are NOT part of the frozen handover contracts above (Task,
 * SafetyEvent, OperatorInsight) — they're additive shapes this app needs.
 * Where one wraps a frozen type (MissionTask), it only ever ADDS fields,
 * never renames or removes one of the frozen ones.
 * ================================================================ */

/**
 * A Mission Board row: the frozen Task shape plus its scheduled start time.
 * `startTime` is presentation-only (e.g. "08:30") — the real backend's
 * equivalent is `start_time` on GET /tasks/today, mapped in lib/api.ts later.
 */
export interface MissionTask extends Task {
  startTime: string;
}

/**
 * One fact in the Pre-Task Threat Briefing. Presented as-is — the frontend
 * does not derive or calculate these, only renders what the backend/AI layer
 * supplies (mocked for now).
 */
export interface ThreatBriefingItem {
  id: string;
  severity: SafetyStatus;
  title: string;
  detail: string;
}

/**
 * Supplementary Active Task facts (why the ETA moved, a rough truck count).
 * Backend/AI-provided; the frontend never computes these.
 */
export interface ActiveTaskInsight {
  taskId: string;
  approxTrucksRemaining: number;
  etaReasons: string[];
}

/** Event categories an operator can log from the Active Task screen. */
export type IncidentEventType = "proximity" | "seatbelt" | "machine" | "ground" | "other";

/**
 * Not a frozen handover contract (no Incident shape was specified) — kept
 * close to the real backend's POST /incidents body (`operator_id`,
 * `machine_id`, `task_id`, `type`, `severity`, `description`) so wiring the
 * real endpoint later is a field-name mapping in lib/api.ts, not a redesign.
 */
export interface IncidentInput {
  eventType: IncidentEventType;
  note: string;
  taskId: string;
  operatorId: string;
  machineId: string;
}

export interface Incident extends IncidentInput {
  id: string;
  createdAt: string;
  /** The backend attaches a recent-telemetry snapshot to every incident (its "Black Box"). */
  hasTelemetryContext: boolean;
}

/* ================================================================
 * Theme + Training Hub + Insights types (Prompt 3)
 *
 * All additive — nothing above is renamed. "Real" values will come from
 * GET /training/recommendations/{operator_id} and GET /insights/operator/{id}/ml
 * (see docs/api/README.md) once wired; the frontend never invents them.
 * ================================================================ */

export type ThemeMode = "light" | "dark";

/** Whether the app's live data is a real backend WebSocket or the local demo/mock feed. */
export type ConnectionMode = "live" | "demo";

/** One entry in the Training Library. Mirrors the backend's clip catalog shape. */
export interface TrainingClip {
  clipId: string;
  title: string;
  description: string;
  durationMin: number;
  category: string;
  /** Local/placeholder video reference — no cloud video infra in this scope. */
  videoRef: string;
}

/**
 * A just-in-time recommendation, e.g. surfaced on Active Task or Training Hub's
 * "Recommended for you". Presentation only — the reason/priority are supplied,
 * never computed in the UI.
 */
export interface TrainingRecommendation {
  clipId: string;
  title: string;
  reason: string;
  durationMin: number;
  priority: "high" | "medium" | "low";
}

/** A bookable instructor slot for the mock booking UI. */
export interface InstructorSlot {
  slotId: string;
  instructorName: string;
  trainingType: string;
  time: string;
}

/** One system-detected behavioural pattern shown on the Habit Radar. */
export interface HabitRadarItem {
  id: string;
  label: string;
  status: "Detected" | "Normal";
}

/** One ranked item on the Focus list — "what to pay attention to right now." */
export interface FocusItem {
  id: string;
  rank: number;
  label: string;
}
