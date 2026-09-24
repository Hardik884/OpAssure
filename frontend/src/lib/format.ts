/** Small presentation-only helpers shared across Mission/Task/Safety components. */
import { CloudIcon, RainIcon, StormIcon, SunIcon } from "@/components/common/icons";
import type { RiskLevel, SafetyStatus } from "@/types";

/** Maps the frozen Task.riskLevel onto the shared safe/warning/critical badge semantics. */
export function riskToStatus(risk: RiskLevel): SafetyStatus {
  if (risk === "high") return "critical";
  if (risk === "medium") return "warning";
  return "safe";
}

/** Weather -> icon lookup. Indexed directly at call sites (never invoked as a factory) so each
 * icon stays the same stable component reference across renders. */
export const WEATHER_ICON: Record<string, typeof SunIcon> = {
  rainy: RainIcon, cloudy: CloudIcon, clear: SunIcon, sunny: SunIcon, storm: StormIcon,
};

export const DEFAULT_WEATHER_ICON = SunIcon;

/** Time-of-day greeting for the Mission Board header. */
export function getGreeting(date: Date = new Date()): string {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
