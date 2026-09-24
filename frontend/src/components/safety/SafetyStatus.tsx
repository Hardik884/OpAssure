/**
 * The persistent safety area — seatbelt / proximity / machine, always visible
 * while the operator is on the Active Task screen (no navigating away to check
 * safety). Reusable so a later WS `safety_alert`/`telemetry_update` feed can
 * update `events` without any change here.
 *
 * Deliberately shows a short status word (not the full SafetyEvent.message
 * sentence, which belongs on the detailed alert components) — this strip is
 * for a one-second glance.
 */
import { MachineIcon, ProximityIcon, SeatbeltIcon } from "@/components/common/icons";
import type { SafetyEvent, SafetyStatus as SafetyLevel } from "@/types";

import { Card, SectionHeader } from "../common/ui";

interface SafetyStatusProps {
  events: SafetyEvent[];
}

interface Row {
  key: string;
  label: string;
  icon: typeof SeatbeltIcon;
  wordFor: Record<SafetyLevel, string>;
}

const ROWS: Row[] = [
  { key: "seatbelt", label: "Seatbelt", icon: SeatbeltIcon, wordFor: { safe: "Fastened", warning: "Check", critical: "Unfastened" } },
  { key: "proximity", label: "Proximity", icon: ProximityIcon, wordFor: { safe: "Clear", warning: "Caution", critical: "Alert" } },
  { key: "machine", label: "Machine", icon: MachineIcon, wordFor: { safe: "Normal", warning: "Check", critical: "Fault" } },
];

const DOT: Record<SafetyLevel, string> = { safe: "bg-safe-500", warning: "bg-warn-500", critical: "bg-critical-500" };
const ICON_TONE: Record<SafetyLevel, string> = { safe: "text-foreground-muted", warning: "text-warn-600", critical: "text-critical-500" };

export function SafetyStatus({ events }: SafetyStatusProps) {
  return (
    <Card data-testid="safety-status">
      <SectionHeader title="Safety" />
      <ul className="space-y-3">
        {ROWS.map(({ key, label, icon: Icon, wordFor }) => {
          // startsWith, not ===, so a live/demo "proximity_alert" event still updates the "proximity" row.
          const severity: SafetyLevel = events.find((e) => e.event.startsWith(key))?.severity ?? "safe";
          return (
            <li key={key} className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-sm font-medium text-foreground-muted">
                <Icon className={`h-4 w-4 shrink-0 ${ICON_TONE[severity]}`} aria-hidden />
                {label}
              </span>
              <span className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
                <span className={`h-2 w-2 rounded-full ${DOT[severity]} ${severity !== "safe" ? "animate-live-pulse" : ""}`} aria-hidden />
                {wordFor[severity]}
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
