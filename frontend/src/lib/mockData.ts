/**
 * Demo mock data — believable stand-in for the backend until the real API is
 * wired in (later prompts). Field names match the frozen types in ../types.
 *
 * Everything is keyed off the shared demo identity (OP1001 / EXC001 / T001) so
 * Mission Board and Active Task (Prompt 2) can pull consistent data without
 * inventing their own fixtures.
 */
import { DEMO_MACHINE_ID, DEMO_OPERATOR_ID, DEMO_TASK_ID } from "@/config/demo";
import type { Machine, Operator, OperatorContext, OperatorInsight, SafetyEvent, Task } from "@/types";

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

export const mockTask: Task = {
  taskId: DEMO_TASK_ID,
  taskType: "truck_loading",
  zone: "A",
  originalEta: 45,
  etaMin: 45,
  etaMax: 45,
  bucketsRemaining: 107,
  weather: "cloudy",
  riskLevel: "low",
};

export const mockSafetyEvents: SafetyEvent[] = [
  {
    event: "seatbelt",
    severity: "safe",
    distance: null,
    direction: null,
    message: "Seatbelt fastened",
  },
  {
    event: "proximity",
    severity: "safe",
    distance: 46,
    direction: "right",
    message: "No worker near the machine",
  },
];

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
