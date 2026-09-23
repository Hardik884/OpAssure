/**
 * One Mission Board row. `variant="primary"` is the current/startable task —
 * visually prominent with a full START TASK action; `variant="secondary"` is a
 * later task with a lighter VIEW action. Same data shape either way (MissionTask).
 */
import type { ReactNode } from "react";

import { riskToStatus, weatherGlyph } from "@/lib/format";
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

  return (
    <Card rounded="lg" className={isPrimary ? "relative overflow-hidden pl-6 sm:pl-7" : ""} data-testid={`task-card-${task.taskId}`}>
      {isPrimary && <span className="absolute inset-y-0 left-0 w-2 bg-brand-500" aria-hidden />}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge>{task.taskId}</Badge>
          <span className="text-sm font-bold tabular-nums text-foreground-muted">{task.startTime}</span>
        </div>
        <StatusBadge status={riskToStatus(task.riskLevel)}>{task.riskLevel} risk</StatusBadge>
      </div>

      <h3 className={`mt-2 font-black uppercase tracking-tight text-foreground ${isPrimary ? "text-2xl sm:text-3xl" : "text-lg"}`}>
        {task.taskType}
      </h3>
      <p className="text-sm font-bold uppercase tracking-wide text-foreground-muted">Zone {task.zone}</p>

      <div className={`mt-4 flex flex-wrap items-end justify-between gap-3 ${isPrimary ? "" : "mt-3"}`}>
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-foreground-muted">ETA</div>
          <div className={`font-black tabular-nums leading-none text-foreground ${isPrimary ? "text-4xl sm:text-5xl" : "text-2xl"}`}>
            {task.etaMin}–{task.etaMax}
            <span className="ml-1 text-sm font-bold text-foreground-muted">min</span>
          </div>
        </div>
        <div className="text-sm font-semibold text-foreground-muted">
          {weatherGlyph(task.weather)} {task.weather}
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
function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-industrial bg-ink-950 px-2 py-1 text-sm font-bold text-white">
      {children}
    </span>
  );
}
