import { weatherGlyph } from "@/lib/format";
import type { HistoryEntry } from "@/types";

import { Card, StatusBadge } from "../common/ui";

export function HistoryEntryCard({ entry }: { entry: HistoryEntry }) {
  return (
    <Card className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-start gap-4">
        <span className="text-sm font-bold tabular-nums text-foreground-muted">{entry.startTime}</span>
        <div>
          <h3 className="font-black uppercase tracking-tight text-foreground">{entry.taskType}</h3>
          <p className="text-sm font-bold uppercase tracking-wide text-foreground-muted">Zone {entry.zone}</p>
          {entry.safetyNote && (
            <p className="mt-1 text-xs font-semibold text-status-warn-fg">⚠ {entry.safetyNote}</p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-lg font-black tabular-nums leading-none text-foreground">
            {entry.etaMin}–{entry.etaMax}
            <span className="ml-1 text-xs font-bold text-foreground-muted">min</span>
          </p>
          <p className="text-xs font-semibold text-foreground-muted">
            {weatherGlyph(entry.weather)} {entry.weather}
          </p>
        </div>
        <StatusBadge status={entry.status === "completed" ? "safe" : "warning"}>
          {entry.status === "completed" ? "Completed" : "Cancelled"}
        </StatusBadge>
      </div>
    </Card>
  );
}
