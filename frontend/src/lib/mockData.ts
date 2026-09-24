/**
 * Demo mock data — believable stand-in for the backend until the real API is
 * wired in (later prompts). Field names match the frozen types in ../types.
 *
 * Everything is keyed off the shared demo identity (OP1001 / EXC001 / T001) so
 * every screen pulls consistent data without inventing its own fixtures.
 */
import { DEMO_MACHINE_ID, DEMO_OPERATOR_ID, DEMO_TASK_ID } from "@/config/demo";
import type {
  ActiveTaskInsight, AthleteProfile, FocusItem, HabitRadarItem, HistoryEntry, Incident, InstructorSlot,
  Machine, MissionTask, Operator, OperatorContext, OperatorInsight, SafetyEvent, Task, ThreatBriefingItem,
  TrainingClip, TrainingImpactCase, TrainingRecommendation,
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

/** Operator Twin — frozen handover example values. */
export const mockOperatorInsight: OperatorInsight = {
  operatorId: DEMO_OPERATOR_ID,
  paceFactor: 0.94,
  rainSensitivity: 0.08,
  fatiguePattern: "afternoon",
  riskLevel: "medium",
};

/** Athlete Card — the Operator Twin's full stat line, mock stand-in for GET /insights/operator/{id}/ml. */
export const mockAthleteProfile: AthleteProfile = {
  operatorId: DEMO_OPERATOR_ID,
  name: "Ravi",
  skill: "Intermediate",
  machineType: "Excavator",
  gamesPlayed: 214,
  paceFactor: 0.94,
  rainSensitivity: 0.08,
  heatSensitivity: 0.11,
  fuelEfficiency: 1.03,
  seatbeltViolationRate: 0.041,
  riskLevel: "medium",
};

/** Training Impact — measured before/after proof, mock stand-in for GET /training/impact. */
export const mockTrainingImpact: TrainingImpactCase[] = [
  {
    operatorId: "OP1003", operatorName: "Earl Murphy", clipTitle: "Cutting avoidable idle",
    metricName: "avoidable_idle_min_per_hour", timestamp: "2025-05-31T06:30:00",
    beforeMetric: 5.393, afterMetric: 3.779, pctChange: -0.299,
  },
  {
    operatorId: "OP1008", operatorName: "Christina Brown", clipTitle: "Cutting avoidable idle",
    metricName: "avoidable_idle_min_per_hour", timestamp: "2025-05-31T06:30:00",
    beforeMetric: 7.165, afterMetric: 3.016, pctChange: -0.579,
  },
  {
    operatorId: "OP1016", operatorName: "Cassandra Sanders", clipTitle: "Smooth swings and braking",
    metricName: "harsh_events_per_hour", timestamp: "2025-06-05T06:30:00",
    beforeMetric: 0.421, afterMetric: 0.252, pctChange: -0.401,
  },
];

/** Training Library — placeholder/local clip references, no cloud video infra. */
export const mockTrainingLibrary: TrainingClip[] = [
  {
    clipId: "CLIP_SEATBELT_01",
    title: "Buckle Up Before You Move",
    description: "Why re-fastening before the machine moves matters, even for short repositions.",
    durationMin: 2,
    category: "Safety",
    videoRef: "/training/clips/seatbelt-01.mp4",
  },
  {
    clipId: "CLIP_WETGROUND_01",
    title: "Wet Ground & Excavation Safety",
    description: "Reading soft/wet ground conditions before and during a dig.",
    durationMin: 3,
    category: "Ground Conditions",
    videoRef: "/training/clips/wet-ground-01.mp4",
  },
  {
    clipId: "CLIP_FATIGUE_01",
    title: "Managing Afternoon Fatigue",
    description: "Recognizing the pace drop that shows up later in a shift and adjusting for it.",
    durationMin: 4,
    category: "Machine Operation",
    videoRef: "/training/clips/fatigue-01.mp4",
  },
  {
    clipId: "CLIP_SMOOTH_01",
    title: "Smooth Cycle Technique",
    description: "Reducing harsh events with smoother bucket-to-truck cycles.",
    durationMin: 3,
    category: "Machine Operation",
    videoRef: "/training/clips/smooth-cycle-01.mp4",
  },
  {
    clipId: "CLIP_IDLE_01",
    title: "Avoidable Idle Awareness",
    description: "Telling truck-wait idle apart from idle that's actually avoidable.",
    durationMin: 2,
    category: "Excavation",
    videoRef: "/training/clips/idle-01.mp4",
  },
];

/** "Recommended for you" — sourced from mock/API data, never calculated in the UI. */
export const mockTrainingRecommendation: TrainingRecommendation = {
  clipId: "CLIP_WETGROUND_01",
  title: "Wet Ground & Excavation Safety",
  reason: "Current task conditions indicate wet ground.",
  durationMin: 2,
  priority: "high",
};

export const mockInstructorSlots: InstructorSlot[] = [
  { slotId: "SLOT_01", instructorName: "J. Alvarez", trainingType: "Seatbelt Habit Coaching", time: "Tomorrow, 07:00" },
  { slotId: "SLOT_02", instructorName: "M. Okafor", trainingType: "Wet Ground Excavation", time: "Tomorrow, 13:00" },
  { slotId: "SLOT_03", instructorName: "J. Alvarez", trainingType: "Smooth Cycle Technique", time: "Thursday, 09:00" },
];

/** Habit Radar — clearly labeled as system-detected patterns, no invented numbers. */
export const mockHabitRadar: HabitRadarItem[] = [
  { id: "afternoon-pace", label: "Afternoon pace reduction", status: "Detected" },
  { id: "wet-ground-slowdown", label: "Wet-ground cycle slowdown", status: "Detected" },
  { id: "safety-attention", label: "Recent safety attention", status: "Normal" },
];

/** Focus — an operator attention aid, not a management priority ranking. */
export const mockFocus: FocusItem[] = [
  { id: "wet-ground", rank: 1, label: "Wet ground" },
  { id: "afternoon-pace", rank: 2, label: "Afternoon pace pattern" },
  { id: "proximity", rank: 3, label: "Proximity awareness" },
];

/** Today's completed activity for /history — same demo tasks the Mission Board shows, as history. */
export const mockHistory: HistoryEntry[] = [
  {
    taskId: "T001",
    taskType: "Earth Excavation",
    zone: "A",
    startTime: "08:30",
    status: "completed",
    etaMin: 52,
    etaMax: 58,
    weather: "Rainy",
    safetyNote: "Proximity alert resolved",
  },
  {
    taskId: "T002",
    taskType: "Trenching",
    zone: "C",
    startTime: "10:00",
    status: "completed",
    etaMin: 43,
    etaMax: 49,
    weather: "Cloudy",
    safetyNote: null,
  },
  {
    taskId: "T003",
    taskType: "Material Loading",
    zone: "B",
    startTime: "14:00",
    status: "completed",
    etaMin: 31,
    etaMax: 35,
    weather: "Clear",
    safetyNote: null,
  },
];

/** A short recent-incidents list for the /safety page — glanceable, not a full incident log UI. */
export const mockRecentIncidents: Incident[] = [
  {
    id: "INC-1042",
    eventType: "proximity",
    note: "Worker walked into swing radius, stopped machine.",
    taskId: DEMO_TASK_ID,
    operatorId: DEMO_OPERATOR_ID,
    machineId: DEMO_MACHINE_ID,
    createdAt: "2025-06-29T08:14:00",
    hasTelemetryContext: true,
  },
  {
    id: "INC-1039",
    eventType: "ground",
    note: "Ground reported wet",
    taskId: DEMO_TASK_ID,
    operatorId: DEMO_OPERATOR_ID,
    machineId: DEMO_MACHINE_ID,
    createdAt: "2025-06-29T07:58:00",
    hasTelemetryContext: true,
  },
];

/** Assembled context for the header/shell/hooks — the shape every screen reads. */
export const mockOperatorContext: OperatorContext = {
  operator: mockOperator,
  machine: mockMachine,
  currentTask: mockTask,
  safetyStatus: "safe",
};
