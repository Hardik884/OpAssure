/**
 * Pre-Task Threat Briefing — a quick-to-scan safety briefing shown before the
 * operator starts a task. Facts only: this presents what the backend/AI layer
 * supplies (mocked for now via lib/api.ts) and invents nothing itself.
 */
import { AlertOctagonIcon, AlertTriangleIcon, CheckIcon } from "@/components/common/icons";
import { Button } from "@/components/common/ui";
import type { MissionTask, SafetyStatus, ThreatBriefingItem } from "@/types";

interface ThreatBriefingProps {
  task: MissionTask;
  /** null while the facts are still loading — distinct from a genuinely empty briefing. */
  items: ThreatBriefingItem[] | null;
  onAcknowledge: () => void;
  onCancel: () => void;
}

export function ThreatBriefing({ task, items, onAcknowledge, onCancel }: ThreatBriefingProps) {
  return (
    <div data-testid="threat-briefing">
      <p className="mb-3 text-sm font-medium text-foreground-muted">
        Before starting {task.taskId} · {task.taskType} · Zone {task.zone}
      </p>

      {items === null ? (
        <p className="text-sm font-medium text-foreground-muted">Loading briefing…</p>
      ) : items.length === 0 ? (
        <p className="text-sm font-medium text-foreground-muted">No briefing items — clear to start.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => {
            const Icon = SEVERITY_ICON[item.severity];
            return (
              <li key={item.id} className={`flex items-start gap-3 rounded-industrial border p-3 ${SEVERITY_STYLE[item.severity]}`}>
                <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
                <div>
                  <p className="font-semibold">{item.title}</p>
                  <p className="text-sm opacity-90">{item.detail}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <Button variant="primary" className="mt-5 w-full" onClick={onAcknowledge}>
        Acknowledge &amp; Start
      </Button>
      <button
        onClick={onCancel}
        className="mt-3 min-h-11 w-full text-center text-sm font-semibold text-foreground-muted underline underline-offset-2 hover:text-foreground"
      >
        Cancel
      </button>
    </div>
  );
}

const SEVERITY_ICON: Record<SafetyStatus, typeof CheckIcon> = { safe: CheckIcon, warning: AlertTriangleIcon, critical: AlertOctagonIcon };
const SEVERITY_STYLE: Record<SafetyStatus, string> = {
  safe: "border-safe-500/30 bg-status-safe-bg text-status-safe-fg",
  warning: "border-warn-500/30 bg-status-warn-bg text-status-warn-fg",
  critical: "border-critical-500/30 bg-status-critical-bg text-status-critical-fg",
};
