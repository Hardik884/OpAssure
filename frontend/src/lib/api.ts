/**
 * The single place the frontend talks to the backend (CLAUDE.md: no fetch calls
 * scattered through components). Every screen/hook goes through the `api` object
 * below, never `fetch` directly.
 *
 * Mock vs real: `USE_MOCK_DATA` (config/env.ts) picks the source. Every function
 * has the same async signature either way.
 *
 * Real-mode mapping happens HERE, at the boundary, never by renaming a field
 * inside a component (CLAUDE.md §10): every backend response is snake_case
 * (see docs/api/README.md); every value handed to a component uses the frozen
 * camelCase types in ../types. This app is scoped to the single demo operator/
 * machine (OP1001/EXC001, config/demo.ts) — every real call below is scoped to
 * that identity, matching how every other part of the project (ml/, backend
 * seed data, docs) treats it as the one live demo identity.
 */
import { DEMO_MACHINE_ID, DEMO_OPERATOR_ID } from "@/config/demo";
import { API_URL, USE_MOCK_DATA } from "@/config/env";
import {
  mockActiveTaskInsightByTask, mockAthleteProfile, mockCriticalProximityAlert, mockFocus, mockHabitRadar,
  mockHistory, mockInstructorSlots, mockMissionTasks, mockOperatorContext, mockOperatorInsight,
  mockRecentIncidents, mockSafetyEvents, mockTask, mockThreatBriefingByTask, mockTrainingImpact,
  mockTrainingLibrary, mockTrainingRecommendation,
} from "@/lib/mockData";
import type {
  ActiveTaskInsight, AthleteProfile, FocusItem, HabitRadarItem, HistoryEntry, Incident, IncidentEventType,
  IncidentInput, InstructorSlot, MissionTask, Operator as OperatorIdentity, Machine as MachineIdentity,
  OperatorContext, OperatorInsight, RiskLevel, SafetyEvent, SafetyStatus, Task, ThreatBriefingItem,
  TrainingClip, TrainingImpactCase, TrainingRecommendation,
} from "@/types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** Generic JSON fetch helper for the real backend. */
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

/* ================================================================
 * Real backend response shapes (snake_case, see docs/api/README.md).
 * Only the fields this file actually reads — not a full mirror of every
 * backend schema. Kept private to this module; components never see these.
 * ================================================================ */

interface OperatorOut {
  operator_id: string;
  name: string;
  skill: string;
}

interface MachineOut {
  machine_id: string;
  type: string;
  model: string;
}

interface TaskOut {
  task_id: string;
  task_type: string;
  zone: string;
  estimated_buckets: number;
  weather: string;
  operator_id: string;
  machine_id: string;
  estimated_time_min: number;
  actual_time_min: number | null;
  start_time: string;
  status: string; // completed | scheduled
}

interface TodayTasksOut {
  date: string;
  operator_id: string;
  tasks: TaskOut[];
}

interface SafetyAlertOut {
  type: string;
  severity: string; // warning | critical
  message: string;
}

interface NearestWorkerOut {
  worker_id: string;
  distance_m: number;
  direction: "front" | "right" | "rear" | "left";
  zone: string;
}

interface SafetyStateOut {
  status: SafetyStatus;
  nearest_worker: NearestWorkerOut | null;
  alerts: SafetyAlertOut[];
}

interface IncidentOut {
  id: number;
  timestamp: string;
  machine_id: string;
  operator_id: string;
  task_id: string | null;
  type: string;
  description: string;
  telemetry_snapshot: unknown[] | null;
}

interface IncidentCreatedOut extends IncidentOut {
  snapshot_size: number;
}

interface IncidentListOut {
  incidents: IncidentOut[];
}

interface LibraryClipOut {
  clip_id: string;
  title: string;
  trigger: string;
  metric_name: string;
  priority: string; // high | medium
}

interface RecommendationOut {
  clip_id: string;
  title: string;
  reason: string;
  priority: string; // high | medium
}

interface RecommendationsOut {
  recommendations: RecommendationOut[];
}

interface TrainingImpactCaseOut {
  operator_id: string;
  operator_name: string;
  clip_title: string;
  metric_name: string;
  timestamp: string;
  before_metric: number;
  after_metric: number;
  pct_change: number | null;
}

/** POST /training/complete response — only `created` is used (rest is server bookkeeping). */
interface TrainingCompleteOut {
  created: boolean;
}

/** One factor in an ETA/twin/risk explanation ({@link build_eta_explanation} etc. in ml/). */
interface MlFactor {
  name: string;
  impact: "positive" | "neutral" | "negative";
  detail?: unknown;
}

interface MlEta {
  eta_min: number;
  eta_max: number;
  eta_point: number;
  original_eta: number;
  reason: string;
  factors: MlFactor[];
  buckets_remaining: number;
}

interface MlDynamicEta extends MlEta {
  pct_complete: number;
  cycle_time_change_pct: number | null;
}

interface MlRemainingWork {
  total_buckets: number;
  buckets_completed: number;
  buckets_remaining: number;
  pct_complete: number;
  trucks_remaining: number | null; // always null — see ml/src/eta/remaining_work.py
}

interface MlRisk {
  risk_level: "low" | "medium" | "high" | "critical";
  score: number;
  factors: string[];
  explanation: string;
}

interface MlHabit {
  habit_type: string;
  count: number;
  opportunities: number;
  frequency: number;
  is_habit: boolean;
  explanation: string;
}

interface MlFocus {
  score: number;
  factors: string[];
  recommendation: string;
}

interface MlOperatorTwin {
  operatorId: string;
  paceFactor: number;
  rainSensitivity: number;
  heatSensitivity: number;
  afternoonEffect: number;
  fuelEfficiency: number;
  seatbeltViolationRate: number;
  nTasks: number;
}

interface MlThreatBriefingItem {
  priority: number;
  risk: string;
  reason: string;
  source: "weather" | "operator" | "machine" | "site" | "safety";
}

/** The full `generate_operator_state()` output (see ml/docs/integration.md §4),
 * minus the internal `_context` key the backend already strips before responding. */
interface MlOperatorState {
  operator_twin: MlOperatorTwin;
  eta: MlEta;
  dynamic_eta: MlDynamicEta;
  remaining_work: MlRemainingWork;
  risk: MlRisk;
  habits: MlHabit[];
  focus: MlFocus;
  training: { recommended: boolean; clip_id?: string; title?: string; reason?: string; duration_seconds?: number };
  threat_briefing: MlThreatBriefingItem[];
}

/* ================================================================
 * Mapping helpers (backend/ML shape -> frozen frontend type).
 * ================================================================ */

/** ml's risk_level has a 4th "critical" band the frontend's 3-band RiskLevel
 * doesn't; critical collapses into "high" — still the most severe UI state,
 * never silently downgraded (the underlying hard-safety-rule score/level is
 * still 100/"critical" in what's shown to the operator via SafetyStatus). */
function toRiskLevel(level: string): RiskLevel {
  return level === "low" ? "low" : level === "medium" ? "medium" : "high";
}

function fetchMlState(operatorId: string, taskId?: string): Promise<MlOperatorState> {
  const qs = taskId ? `?task_id=${encodeURIComponent(taskId)}` : "";
  return request<MlOperatorState>(`/insights/operator/${encodeURIComponent(operatorId)}/ml${qs}`);
}

function mapTask(t: TaskOut, eta: { eta_min: number; eta_max: number; original_eta: number }, riskLevel: RiskLevel): Task {
  return {
    taskId: t.task_id,
    taskType: t.task_type,
    zone: t.zone,
    originalEta: Math.round(eta.original_eta),
    etaMin: Math.round(eta.eta_min),
    etaMax: Math.round(eta.eta_max),
    bucketsRemaining: t.estimated_buckets,
    weather: t.weather,
    riskLevel,
  };
}

async function fetchTaskWithMlEta(taskOut: TaskOut): Promise<Task> {
  const state = await fetchMlState(taskOut.operator_id, taskOut.task_id);
  return mapTask(taskOut, state.eta, toRiskLevel(state.risk.risk_level));
}

function formatStartTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const DIRECTION_VALUES: readonly string[] = ["front", "right", "rear", "left"];

function mapSafetyEvent(alert: SafetyAlertOut, nearestWorker: NearestWorkerOut | null): SafetyEvent {
  const isProximity = alert.type === "proximity";
  const direction = isProximity && nearestWorker && DIRECTION_VALUES.includes(nearestWorker.direction)
    ? (nearestWorker.direction as SafetyEvent["direction"])
    : null;
  return {
    event: alert.type,
    severity: alert.severity === "critical" ? "critical" : "warning",
    distance: isProximity && nearestWorker ? nearestWorker.distance_m : null,
    direction,
    message: alert.message,
  };
}

const INCIDENT_TYPE_MAP: Record<string, IncidentEventType> = {
  seatbelt: "seatbelt",
  proximity: "proximity",
  near_miss: "proximity",
  proximity_near_miss: "proximity",
  harsh_event: "machine",
  machine: "machine",
  ground: "ground",
  manual_report: "other",
};

function mapIncidentType(backendType: string): IncidentEventType {
  return INCIDENT_TYPE_MAP[backendType] ?? "other";
}

function mapIncident(i: IncidentOut): Incident {
  return {
    id: String(i.id),
    eventType: mapIncidentType(i.type),
    note: i.description,
    taskId: i.task_id ?? "",
    operatorId: i.operator_id,
    machineId: i.machine_id,
    createdAt: i.timestamp,
    hasTelemetryContext: !!i.telemetry_snapshot && i.telemetry_snapshot.length > 0,
  };
}

/** Cosmetic defaults for fields the backend's clip catalog doesn't carry
 * (description/videoRef/durationMin — see docs/api/README.md's note on
 * `/training/library`). Never used for a computed number, only presentation. */
const DEFAULT_CLIP_DURATION_MIN = 5;

function mapLibraryClip(c: LibraryClipOut): TrainingClip {
  return {
    clipId: c.clip_id,
    title: c.title,
    description: `Addresses ${c.trigger.replace(/_/g, " ")} (${c.metric_name.replace(/_/g, " ")}).`,
    durationMin: DEFAULT_CLIP_DURATION_MIN,
    category: c.trigger,
    videoRef: `/training/${c.clip_id}.mp4`,
  };
}

function mapRecommendation(r: RecommendationOut): TrainingRecommendation {
  return {
    clipId: r.clip_id,
    title: r.title,
    reason: r.reason,
    durationMin: DEFAULT_CLIP_DURATION_MIN,
    priority: r.priority === "high" ? "high" : "medium",
  };
}

function mapImpactCase(c: TrainingImpactCaseOut): TrainingImpactCase {
  return {
    operatorId: c.operator_id,
    operatorName: c.operator_name,
    clipTitle: c.clip_title,
    metricName: c.metric_name,
    timestamp: c.timestamp,
    beforeMetric: c.before_metric,
    afterMetric: c.after_metric,
    pctChange: c.pct_change,
  };
}

function mapThreatBriefingItem(item: MlThreatBriefingItem): ThreatBriefingItem {
  return {
    id: `tb-${item.priority}`,
    // The ML layer ranks by severity but doesn't emit a safety-status band —
    // the top-ranked safety-sourced risk is the one the hard safety rules
    // would also flag as critical; everything else is a lower-grade warning.
    severity: item.priority === 1 && item.source === "safety" ? "critical" : "warning",
    title: item.risk,
    detail: item.reason,
  };
}

export interface JudgeTriggerResult {
  triggered: boolean;
}

async function postJudgeEvent(path: string, body: Record<string, unknown>): Promise<JudgeTriggerResult> {
  const result = await request<{ triggered?: boolean; events: unknown[] }>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { triggered: result.triggered ?? result.events.length > 0 };
}

export const api = {
  /** Operator, machine, current task and overall safety status in one shape. */
  async getOperatorContext(): Promise<OperatorContext> {
    if (USE_MOCK_DATA) return mockResolve(mockOperatorContext);

    const [operatorOut, today] = await Promise.all([
      request<OperatorOut>(`/operators/${DEMO_OPERATOR_ID}`),
      request<TodayTasksOut>(`/tasks/today?operator_id=${DEMO_OPERATOR_ID}`),
    ]);
    const currentTaskOut = today.tasks.find((t) => t.status !== "completed") ?? null;

    const [machineOut, safety] = await Promise.all([
      request<MachineOut>(`/machines/${currentTaskOut?.machine_id ?? DEMO_MACHINE_ID}`),
      request<SafetyStateOut>(`/safety/${currentTaskOut?.machine_id ?? DEMO_MACHINE_ID}`).catch(
        () => null as SafetyStateOut | null,
      ),
    ]);

    const operator: OperatorIdentity = { operatorId: operatorOut.operator_id, name: operatorOut.name, skill: operatorOut.skill };
    const machine: MachineIdentity = { machineId: machineOut.machine_id, type: machineOut.type, model: machineOut.model };
    const currentTask = currentTaskOut ? await fetchTaskWithMlEta(currentTaskOut) : null;

    return { operator, machine, currentTask, safetyStatus: safety?.status ?? "safe" };
  },

  async getCurrentTask(): Promise<Task> {
    if (USE_MOCK_DATA) return mockResolve(mockTask);
    const today = await request<TodayTasksOut>(`/tasks/today?operator_id=${DEMO_OPERATOR_ID}`);
    const currentTaskOut = today.tasks.find((t) => t.status !== "completed") ?? today.tasks[0];
    if (!currentTaskOut) throw new ApiError(404, `No task found for ${DEMO_OPERATOR_ID} today`);
    return fetchTaskWithMlEta(currentTaskOut);
  },

  async getSafetyEvents(): Promise<SafetyEvent[]> {
    if (USE_MOCK_DATA) return mockResolve(mockSafetyEvents);
    const state = await request<SafetyStateOut>(`/safety/${DEMO_MACHINE_ID}`);
    return state.alerts.map((alert) => mapSafetyEvent(alert, state.nearest_worker));
  },

  async getOperatorInsight(): Promise<OperatorInsight> {
    if (USE_MOCK_DATA) return mockResolve(mockOperatorInsight);
    const state = await fetchMlState(DEMO_OPERATOR_ID);
    const twin = state.operator_twin;
    return {
      operatorId: twin.operatorId,
      paceFactor: twin.paceFactor,
      rainSensitivity: twin.rainSensitivity,
      fatiguePattern:
        twin.afternoonEffect <= -0.03
          ? `Afternoon pace drops ~${Math.round(Math.abs(twin.afternoonEffect) * 100)}% (${twin.nTasks} tasks observed)`
          : "No significant afternoon pattern observed",
      riskLevel: toRiskLevel(state.risk.risk_level),
    };
  },

  /** The operator's full "stat card" for the Insights page — same operator_twin
   * data as getOperatorInsight(), just unabridged (every stat, not the frozen
   * 3-field subset), plus static identity/machine facts for the card header. */
  async getAthleteProfile(): Promise<AthleteProfile> {
    if (USE_MOCK_DATA) return mockResolve(mockAthleteProfile);
    const [state, operatorOut, machineOut] = await Promise.all([
      fetchMlState(DEMO_OPERATOR_ID),
      request<OperatorOut>(`/operators/${DEMO_OPERATOR_ID}`),
      request<MachineOut>(`/machines/${DEMO_MACHINE_ID}`),
    ]);
    const twin = state.operator_twin;
    return {
      operatorId: twin.operatorId,
      name: operatorOut.name,
      skill: operatorOut.skill,
      machineType: machineOut.type,
      gamesPlayed: twin.nTasks,
      paceFactor: twin.paceFactor,
      rainSensitivity: twin.rainSensitivity,
      heatSensitivity: twin.heatSensitivity,
      fuelEfficiency: twin.fuelEfficiency,
      seatbeltViolationRate: twin.seatbeltViolationRate,
      riskLevel: toRiskLevel(state.risk.risk_level),
    };
  },

  /** Fleet-wide proof that completed training changed real behavior — every
   * case is a measured before/after pair from training_events, never modeled. */
  async getTrainingImpact(): Promise<TrainingImpactCase[]> {
    if (USE_MOCK_DATA) return mockResolve(mockTrainingImpact);
    const result = await request<{ cases: TrainingImpactCaseOut[] }>("/training/impact");
    return result.cases.map(mapImpactCase);
  },

  /** Mission Board rows for today, in schedule order. Uses each task's own
   * plan estimate (not a per-row ML call — see docs/api/README.md's note on
   * why only the active task gets a live personalized ETA). */
  async getTodayTasks(): Promise<MissionTask[]> {
    if (USE_MOCK_DATA) return mockResolve(mockMissionTasks);
    const today = await request<TodayTasksOut>(`/tasks/today?operator_id=${DEMO_OPERATOR_ID}`);
    return today.tasks.map((t) => ({
      ...mapTask(t, { eta_min: t.estimated_time_min, eta_max: t.estimated_time_min, original_eta: t.estimated_time_min }, "low"),
      startTime: formatStartTime(t.start_time),
    }));
  },

  /** A single task by id (Mission Board's "VIEW" action). */
  async getTask(taskId: string): Promise<Task | undefined> {
    if (USE_MOCK_DATA) return mockResolve(mockMissionTasks.find((t) => t.taskId === taskId));
    const taskOut = await request<TaskOut>(`/tasks/${encodeURIComponent(taskId)}`);
    return fetchTaskWithMlEta(taskOut);
  },

  /** Pre-Task Threat Briefing facts for a task (empty if there's nothing to brief). */
  async getThreatBriefing(taskId: string): Promise<ThreatBriefingItem[]> {
    if (USE_MOCK_DATA) return mockResolve(mockThreatBriefingByTask[taskId] ?? []);
    const state = await fetchMlState(DEMO_OPERATOR_ID, taskId);
    return state.threat_briefing.map(mapThreatBriefingItem);
  },

  /** Supplementary Active Task facts (ETA reasons, remaining work). ml/ never
   * fabricates a truck count (no bucket-per-truck field in the data model —
   * see ml/src/eta/remaining_work.py), so this surfaces the real
   * buckets-remaining count and says so explicitly in the reason text rather
   * than inventing a truck number. */
  async getActiveTaskInsight(taskId: string): Promise<ActiveTaskInsight | null> {
    if (USE_MOCK_DATA) return mockResolve(mockActiveTaskInsightByTask[taskId] ?? null);
    const state = await fetchMlState(DEMO_OPERATOR_ID, taskId);
    const reasons = [state.dynamic_eta.reason];
    if (state.remaining_work.trucks_remaining === null) {
      reasons.push(`Truck count not tracked — ${state.remaining_work.buckets_remaining} buckets remaining`);
    }
    return {
      taskId,
      approxTrucksRemaining: state.remaining_work.trucks_remaining ?? state.remaining_work.buckets_remaining,
      etaReasons: reasons,
    };
  },

  /** Records an operator-reported incident. Always returns a telemetry-attached record. */
  async recordIncident(input: IncidentInput): Promise<Incident> {
    if (USE_MOCK_DATA) {
      const incident: Incident = {
        ...input,
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
        hasTelemetryContext: true,
      };
      return mockResolve(incident);
    }
    const created = await request<IncidentCreatedOut>("/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operator_id: input.operatorId,
        machine_id: input.machineId,
        task_id: input.taskId,
        type: input.eventType,
        description: input.note,
      }),
    });
    return mapIncident(created);
  },

  /**
   * Demo-only: stands in for a live WS `proximity_alert` event until realtime
   * integration lands. Returns the frozen critical example every time.
   */
  triggerDemoProximityAlert(): Promise<SafetyEvent> {
    return mockResolve(mockCriticalProximityAlert, 50);
  },

  /** Training Hub library — all available clips. */
  async getTrainingLibrary(): Promise<TrainingClip[]> {
    if (USE_MOCK_DATA) return mockResolve(mockTrainingLibrary);
    const clips = await request<LibraryClipOut[]>("/training/library");
    return clips.map(mapLibraryClip);
  },

  /** The single "Recommended for you" / just-in-time recommendation, if any. */
  async getTrainingRecommendation(): Promise<TrainingRecommendation | null> {
    if (USE_MOCK_DATA) return mockResolve(mockTrainingRecommendation);
    const result = await request<RecommendationsOut>(`/training/recommendations/${DEMO_OPERATOR_ID}`);
    return result.recommendations.length > 0 ? mapRecommendation(result.recommendations[0]) : null;
  },

  /** Mock instructor booking slots — intentionally not a real scheduling system. */
  getInstructorSlots(): Promise<InstructorSlot[]> {
    return mockResolve(mockInstructorSlots);
  },

  /** Record that the operator watched a training clip (Training Hub "Watch" actions). */
  async completeTraining(clipId: string): Promise<void> {
    if (USE_MOCK_DATA) {
      await mockResolve(undefined);
      return;
    }
    await request<TrainingCompleteOut>("/training/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator_id: DEMO_OPERATOR_ID, clip_id: clipId }),
    });
  },

  /** Habit Radar — system-detected behavioural patterns, glanceable only. */
  async getHabitRadar(): Promise<HabitRadarItem[]> {
    if (USE_MOCK_DATA) return mockResolve(mockHabitRadar);
    const state = await fetchMlState(DEMO_OPERATOR_ID);
    return state.habits.map((h) => ({
      id: h.habit_type,
      label: h.explanation,
      status: h.is_habit ? "Detected" : "Normal",
    }));
  },

  /** Focus — "what should the operator pay attention to right now," ranked. */
  async getFocus(): Promise<FocusItem[]> {
    if (USE_MOCK_DATA) return mockResolve(mockFocus);
    const state = await fetchMlState(DEMO_OPERATOR_ID);
    return state.focus.factors.map((label, index) => ({ id: `focus-${index}`, rank: index + 1, label }));
  },

  /** Today's completed activity for /history. */
  async getTaskHistory(): Promise<HistoryEntry[]> {
    if (USE_MOCK_DATA) return mockResolve(mockHistory);
    const [today, incidentsResult] = await Promise.all([
      request<TodayTasksOut>(`/tasks/today?operator_id=${DEMO_OPERATOR_ID}`),
      request<IncidentListOut>(`/incidents/${DEMO_OPERATOR_ID}`).catch(() => ({ incidents: [] }) as IncidentListOut),
    ]);
    const incidentByTask = new Map(incidentsResult.incidents.filter((i) => i.task_id).map((i) => [i.task_id, i]));
    return today.tasks
      .filter((t) => t.status === "completed")
      .map((t) => {
        const minutes = Math.round(t.actual_time_min ?? t.estimated_time_min);
        return {
          taskId: t.task_id,
          taskType: t.task_type,
          zone: t.zone,
          startTime: formatStartTime(t.start_time),
          status: "completed" as const,
          etaMin: minutes,
          etaMax: minutes,
          weather: t.weather,
          safetyNote: incidentByTask.get(t.task_id)?.type ?? null,
        };
      });
  },

  /** A short recent-incidents list for the /safety page. */
  async getRecentIncidents(): Promise<Incident[]> {
    if (USE_MOCK_DATA) return mockResolve(mockRecentIncidents);
    const result = await request<IncidentListOut>(`/incidents/${DEMO_OPERATOR_ID}`);
    return result.incidents.map(mapIncident);
  },

  /* ================================================================
   * Judge Control Panel — live-demo only. Every call here just feeds a
   * synthetic-but-plausible input through the backend's real rule engine/ETA
   * pipeline (see backend/app/api/judge.py); the frontend never fabricates
   * the resulting ETA/safety numbers, only triggers the same recompute the
   * live replay itself uses.
   * ================================================================ */

  /** Whether the T001 replay is currently running (injections need it running). */
  async getDemoStatus(): Promise<{ running: boolean }> {
    if (USE_MOCK_DATA) return mockResolve({ running: false });
    const result = await request<{ status: { state: string } }>("/demo/status");
    return { running: result.status.state === "running" };
  },

  /** Starts the T001 replay (no-op if already running). */
  async startDemoReplay(): Promise<{ started: boolean }> {
    if (USE_MOCK_DATA) return mockResolve({ started: false });
    return request<{ started: boolean }>("/demo/start", { method: "POST" });
  },

  async triggerProximityIntrusion(): Promise<JudgeTriggerResult> {
    if (USE_MOCK_DATA) return mockResolve({ triggered: false });
    return postJudgeEvent("/judge/proximity", { distance_m: 8, direction: "right" });
  },

  async triggerRainstorm(): Promise<JudgeTriggerResult> {
    if (USE_MOCK_DATA) return mockResolve({ triggered: false });
    return postJudgeEvent("/judge/rain", { rain_mm: 15, cycle_multiplier: 1.4 });
  },

  async triggerCycleSpike(): Promise<JudgeTriggerResult> {
    if (USE_MOCK_DATA) return mockResolve({ triggered: false });
    return postJudgeEvent("/judge/cycle-spike", { multiplier: 1.7 });
  },

  /** Clears every judge-triggered override (rain, cycle spike, proximity) without stopping the replay. */
  async resetJudgeOverrides(): Promise<JudgeTriggerResult> {
    if (USE_MOCK_DATA) return mockResolve({ triggered: false });
    return postJudgeEvent("/judge/reset", {});
  },
};

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong";
}
