/**
 * Pre-Task Threat Briefing — a quick-to-scan safety briefing shown before the
 * operator starts a task. Facts only: this presents what the backend/AI layer
 * supplies (mocked for now via lib/api.ts) and invents nothing itself.
 */
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
      <p className="mb-3 text-sm font-semibold text-line-500">
        Before starting {task.taskId} · {task.taskType} · Zone {task.zone}
      </p>

      {items === null ? (
        <p className="text-sm font-medium text-line-500">Loading briefing…</p>
      ) : items.length === 0 ? (
        <p className="text-sm font-medium text-line-500">No briefing items — clear to start.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id} className={`flex items-start gap-3 rounded-industrial border-2 p-3 ${SEVERITY_STYLE[item.severity]}`}>
              <span className="mt-0.5 shrink-0 text-lg" aria-hidden>
                {SEVERITY_ICON[item.severity]}
              </span>
              <div>
                <p className="font-bold text-ink-950">{item.title}</p>
                <p className="text-sm text-ink-700">{item.detail}</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Button variant="primary" className="mt-5 w-full" onClick={onAcknowledge}>
        Acknowledge &amp; Start
      </Button>
      <button
        onClick={onCancel}
        className="mt-3 min-h-11 w-full text-center text-sm font-bold uppercase tracking-wide text-line-500 underline hover:text-ink-950"
      >
        Cancel
      </button>
    </div>
  );
}

const SEVERITY_ICON: Record<SafetyStatus, string> = { safe: "✓", warning: "⚠", critical: "⛔" };
const SEVERITY_STYLE: Record<SafetyStatus, string> = {
  safe: "border-safe-500 bg-safe-bg",
  warning: "border-warn-500 bg-warn-bg",
  critical: "border-critical-500 bg-critical-bg",
};
