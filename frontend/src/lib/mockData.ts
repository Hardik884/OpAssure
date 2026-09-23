/**
 * Demo mock data — believable stand-in for the backend until the real API is
 * wired in (later prompts). Field names match the frozen types in ../types.
 *
 * Everything is keyed off the shared demo identity (OP1001 / EXC001 / T001) so
 * every screen pulls consistent data without inventing its own fixtures.
 */
import { DEMO_MACHINE_ID, DEMO_OPERATOR_ID, DEMO_TASK_ID } from "@/config/demo";
import type {
  ActiveTaskInsight, Machine, MissionTask, Operator, OperatorContext, OperatorInsight, SafetyEvent,
  Task, ThreatBriefingItem,
} from "@/types";

export const mockOperator: Operator = {
  operatorId: DEMO_OPERATOR_ID,
  name: "Ravi",
  skill: "Intermediate",
};

export const mockMachine: Machine = {
  machineId: DEMO_MACHINE_ID,
  type: "excavator",
  model: "CAT 320",
};

/**
 * Today's mission, in schedule order. T001 (the frozen handover example) is the
 * current/startable task; T002/T003 are illustrative mock rows for later in the
 * shift — their numbers aren't specified by the handover, only their display copy.
 */
export const mockMissionTasks: MissionTask[] = [
  {
    taskId: DEMO_TASK_ID,
    taskType: "Earth Excavation",
    zone: "A",
    originalEta: 45,
    etaMin: 52,
    etaMax: 58,
    bucketsRemaining: 22,
    weather: "Rainy",
    riskLevel: "medium",
    startTime: "08:30",
  },
  {
    taskId: "T002",
    taskType: "Trenching",
    zone: "C",
    originalEta: 46,
    etaMin: 43,
    etaMax: 49,
    bucketsRemaining: 34,
    weather: "Cloudy",
    riskLevel: "low",
    startTime: "10:00",
  },
  {
    taskId: "T003",
    taskType: "Material Loading",
    zone: "B",
    originalEta: 33,
    etaMin: 31,
    etaMax: 35,
    bucketsRemaining: 19,
    weather: "Clear",
    riskLevel: "low",
    startTime: "14:00",
  },
];

/** The operator's current/active task — T001, the same object as the board's first row. */
export const mockTask: Task = mockMissionTasks[0];

/** Pre-Task Threat Briefing facts, keyed by task — only T001 is startable in this demo. */
export const mockThreatBriefingByTask: Record<string, ThreatBriefingItem[]> = {
  [DEMO_TASK_ID]: [
    { id: "wet-ground", severity: "warning", title: "Wet ground", detail: "Increased trench risk" },
    { id: "pace-drop", severity: "warning", title: "Pace drops after 2:30 PM", detail: "Known fatigue pattern" },
    { id: "zone-history", severity: "warning", title: "Previous zone issue", detail: "Rock encountered at 1.2m" },
  ],
};

/** Supplementary Active Task facts (the "WHY?" behind the ETA, and the truck estimate). */
export const mockActiveTaskInsightByTask: Record<string, ActiveTaskInsight> = {
  [DEMO_TASK_ID]: {
    taskId: DEMO_TASK_ID,
    approxTrucksRemaining: 3,
    etaReasons: ["Rain increased", "Cycle time +15%"],
  },
};

export const mockSafetyEvents: SafetyEvent[] = [
  { event: "seatbelt", severity: "safe", distance: null, direction: null, message: "Seatbelt fastened" },
  { event: "proximity", severity: "safe", distance: 46, direction: "right", message: "No worker near the machine" },
  { event: "machine", severity: "safe", distance: null, direction: null, message: "Machine operating normally" },
];

/**
 * The frozen critical proximity example. Stands in for a live WS `proximity_alert`
 * event until realtime is wired in — see api.triggerDemoProximityAlert().
 */
export const mockCriticalProximityAlert: SafetyEvent = {
  event: "proximity_alert",
  severity: "critical",
  distance: 12,
  direction: "right",
  message: "Worker detected on right",
};

export const mockOperatorInsight: OperatorInsight = {
  operatorId: DEMO_OPERATOR_ID,
  paceFactor: 1.01,
  rainSensitivity: 0.28,
  fatiguePattern: "Slower after 14:00, worse on hot afternoons",
  riskLevel: "low",
};

/** Assembled context for the header/shell/hooks — the shape every screen reads. */
export const mockOperatorContext: OperatorContext = {
  operator: mockOperator,
  machine: mockMachine,
  currentTask: mockTask,
  safetyStatus: "safe",
};
