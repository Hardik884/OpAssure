import { AlertTriangleIcon } from "@/components/common/icons";
import { DEFAULT_WEATHER_ICON, WEATHER_ICON } from "@/lib/format";
import type { HistoryEntry } from "@/types";

import { Card, StatusBadge } from "../common/ui";

export function HistoryEntryCard({ entry }: { entry: HistoryEntry }) {
  const WeatherIcon = WEATHER_ICON[entry.weather.trim().toLowerCase()] ?? DEFAULT_WEATHER_ICON;
  return (
    <Card className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-start gap-4">
        <span className="text-sm font-semibold tabular-nums text-foreground-muted">{entry.startTime}</span>
        <div>
          <h3 className="font-display font-semibold tracking-tight text-foreground">{entry.taskType}</h3>
          <p className="text-sm font-medium text-foreground-muted">Zone {entry.zone}</p>
          {entry.safetyNote && (
            <p className="mt-1 flex items-center gap-1 text-xs font-semibold text-status-warn-fg">
              <AlertTriangleIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
              {entry.safetyNote}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="font-display text-lg font-semibold tabular-nums leading-none text-foreground">
            {entry.etaMin === entry.etaMax ? entry.etaMin : `${entry.etaMin}–${entry.etaMax}`}
            <span className="ml-1 text-xs font-medium text-foreground-muted">min</span>
          </p>
          <p className="flex items-center justify-end gap-1 text-xs font-medium text-foreground-muted">
            <WeatherIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
            {entry.weather}
          </p>
        </div>
        <StatusBadge status={entry.status === "completed" ? "safe" : "warning"}>
          {entry.status === "completed" ? "Completed" : "Cancelled"}
        </StatusBadge>
      </div>
    </Card>
  );
}
