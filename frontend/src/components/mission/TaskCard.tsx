/**
 * One Mission Board row. `variant="primary"` is the current/startable task —
 * visually prominent with a full Start Task action; `variant="secondary"` is a
 * later task with a lighter View action. Same data shape either way (MissionTask).
 */
import type { ReactNode } from "react";

import { DEFAULT_WEATHER_ICON, riskToStatus, WEATHER_ICON } from "@/lib/format";
import type { MissionTask } from "@/types";

import { Button, Card, StatusBadge } from "../common/ui";

interface TaskCardProps {
  task: MissionTask;
  variant: "primary" | "secondary";
  onStart?: () => void;
  onView?: () => void;
}

export function TaskCard({ task, variant, onStart, onView }: TaskCardProps) {
  const isPrimary = variant === "primary";
  const WeatherIcon = WEATHER_ICON[task.weather.trim().toLowerCase()] ?? DEFAULT_WEATHER_ICON;

  return (
    <Card rounded="lg" tone={isPrimary ? "dark" : "light"} data-testid={`task-card-${task.taskId}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge dark={isPrimary}>{task.taskId}</Badge>
          <span className={`text-sm font-semibold tabular-nums ${isPrimary ? "text-line-400" : "text-foreground-muted"}`}>
            {task.startTime}
          </span>
        </div>
        <StatusBadge status={riskToStatus(task.riskLevel)}>{task.riskLevel} risk</StatusBadge>
      </div>

      <h3 className={`mt-2.5 font-display font-semibold tracking-tight ${isPrimary ? "text-2xl sm:text-3xl" : "text-lg text-foreground"}`}>
        {task.taskType}
      </h3>
      <p className={`text-sm font-medium ${isPrimary ? "text-line-400" : "text-foreground-muted"}`}>Zone {task.zone}</p>

      <div className={`mt-4 flex flex-wrap items-end justify-between gap-3 ${isPrimary ? "" : "mt-3"}`}>
        <div>
          <div className={`text-xs font-semibold uppercase tracking-[0.1em] ${isPrimary ? "text-line-400" : "text-foreground-muted"}`}>
            ETA
          </div>
          <div className={`font-display font-semibold tabular-nums leading-none ${isPrimary ? "text-4xl sm:text-5xl" : "text-2xl text-foreground"}`}>
            {task.etaMin === task.etaMax ? task.etaMin : `${task.etaMin}–${task.etaMax}`}
            <span className={`ml-1 text-sm font-medium ${isPrimary ? "text-line-400" : "text-foreground-muted"}`}>min</span>
          </div>
        </div>
        <div className={`flex items-center gap-1.5 text-sm font-medium ${isPrimary ? "text-line-300" : "text-foreground-muted"}`}>
          <WeatherIcon className="h-4 w-4 shrink-0" aria-hidden />
          {task.weather}
        </div>
      </div>

      {isPrimary ? (
        <Button variant="primary" className="mt-4 w-full" onClick={onStart}>
          Start Task
        </Button>
      ) : (
        <Button variant="ghost" className="mt-4 w-full" onClick={onView}>
          View
        </Button>
      )}
    </Card>
  );
}

/** A subtle badge used for the task-id chip — reuses StatusBadge's visual weight without a status color. */
function Badge({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
        dark ? "bg-white/10 text-white" : "bg-ink-950 text-white"
      }`}
    >
      {children}
    </span>
  );
}
