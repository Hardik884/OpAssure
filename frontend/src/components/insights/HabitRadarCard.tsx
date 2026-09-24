/**
 * Habit Radar — clearly labeled as system-detected patterns, not a claim of
 * unsupported numerical precision. Glanceable, not a data table.
 */
import type { HabitRadarItem } from "@/types";

import { Card, SectionHeader } from "../common/ui";

export function HabitRadarCard({ habits }: { habits: HabitRadarItem[] }) {
  return (
    <Card rounded="lg">
      <SectionHeader title="Habit Radar" />
      <ul className="space-y-3">
        {habits.map((habit) => (
          <li key={habit.id} className="flex items-center justify-between gap-3">
            <span className="min-w-0 flex-1 text-sm font-semibold leading-snug text-foreground">{habit.label}</span>
            <span
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-industrial px-2.5 py-1 text-xs font-bold uppercase tracking-wide ${
                habit.status === "Detected" ? "bg-status-warn-bg text-status-warn-fg" : "bg-status-safe-bg text-status-safe-fg"
              }`}
            >
              <span aria-hidden>{habit.status === "Detected" ? "●" : "✓"}</span>
              {habit.status}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
