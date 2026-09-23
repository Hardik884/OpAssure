/** Small presentation-only helpers shared across Mission/Task/Safety components. */
import type { RiskLevel, SafetyStatus } from "@/types";

/** Maps the frozen Task.riskLevel onto the shared safe/warning/critical badge semantics. */
export function riskToStatus(risk: RiskLevel): SafetyStatus {
  if (risk === "high") return "critical";
  if (risk === "medium") return "warning";
  return "safe";
}

const WEATHER_GLYPH: Record<string, string> = {
  rainy: "🌧", cloudy: "☁", clear: "☀", sunny: "☀", storm: "⛈",
};

/** A tiny glyph for a weather label — decorative only, always paired with the text. */
export function weatherGlyph(weather: string): string {
  return WEATHER_GLYPH[weather.trim().toLowerCase()] ?? "•";
}

/** Time-of-day greeting for the Mission Board header. */
export function getGreeting(date: Date = new Date()): string {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
