import {
  HistoryIcon, InsightsIcon, MissionIcon, SafetyIcon, TaskIcon, TrainingIcon,
} from "@/components/common/icons";
import type { NavKey } from "@/types";

export interface NavItem {
  key: NavKey;
  label: string;
  href: string;
  icon: typeof MissionIcon;
}

/** Order matches the operator's natural workflow: plan -> do -> stay safe -> improve -> review. */
export const NAV_ITEMS: NavItem[] = [
  { key: "mission", label: "Mission", href: "/mission", icon: MissionIcon },
  { key: "task", label: "Task", href: "/task", icon: TaskIcon },
  { key: "safety", label: "Safety", href: "/safety", icon: SafetyIcon },
  { key: "training", label: "Training", href: "/training", icon: TrainingIcon },
  { key: "insights", label: "Insights", href: "/insights", icon: InsightsIcon },
  { key: "history", label: "History", href: "/history", icon: HistoryIcon },
];
