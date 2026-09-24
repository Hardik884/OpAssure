/**
 * Proven Impact — the "athlete improved" half of the athlete-card story.
 * Every number here is a measured before/after pair from `training_events`
 * (GET /training/impact), never a projection: this only ever shows a case
 * once a real "after" value has been recorded, so there's nothing to invent
 * or interpret (CLAUDE.md §1 principle 5).
 */
import { TrendDownIcon, TrendUpIcon } from "@/components/common/icons";
import type { TrainingImpactCase } from "@/types";

import { Card, Empty, SectionHeader } from "../common/ui";

function metricLabel(metricName: string): string {
  return metricName.replace(/_/g, " ");
}

export function TrainingImpactCard({ cases }: { cases: TrainingImpactCase[] }) {
  return (
    <Card rounded="lg" data-testid="training-impact-card">
      <SectionHeader title="Proven Impact — Fleet Coaching Results" />
      {cases.length === 0 ? (
        <Empty>No measured before/after results yet.</Empty>
      ) : (
        <ul className="space-y-4">
          {cases.map((c, i) => (
            <ImpactRow key={`${c.operatorId}-${c.metricName}-${i}`} case={c} />
          ))}
        </ul>
      )}
    </Card>
  );
}

function ImpactRow({ case: c }: { case: TrainingImpactCase }) {
  const improved = c.pctChange !== null && c.pctChange < 0;
  const TrendIcon = improved ? TrendDownIcon : TrendUpIcon;
  const beforeWidth = 100;
  const afterWidth = c.beforeMetric > 0 ? Math.min(100, Math.round((c.afterMetric / c.beforeMetric) * 100)) : 0;

  return (
    <li className="border-t border-border pt-4 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-foreground">
          {c.operatorName} <span className="font-medium text-foreground-muted">&middot; {c.clipTitle}</span>
        </p>
        {c.pctChange !== null && (
          <span
            className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              improved ? "bg-status-safe-bg text-status-safe-fg" : "bg-status-warn-bg text-status-warn-fg"
            }`}
          >
            <TrendIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
            {Math.abs(Math.round(c.pctChange * 100))}%
          </span>
        )}
      </div>
      <p className="mt-0.5 text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">
        {metricLabel(c.metricName)}
      </p>

      <div className="mt-2 space-y-1.5">
        <BarRow label="Before" value={c.beforeMetric} widthPct={beforeWidth} tone="muted" />
        <BarRow label="After" value={c.afterMetric} widthPct={afterWidth} tone={improved ? "safe" : "warn"} />
      </div>
    </li>
  );
}

function BarRow({
  label,
  value,
  widthPct,
  tone,
}: {
  label: string;
  value: number;
  widthPct: number;
  tone: "muted" | "safe" | "warn";
}) {
  const barColor = tone === "safe" ? "bg-safe-500" : tone === "warn" ? "bg-warn-500" : "bg-foreground-muted/40";
  return (
    <div className="flex items-center gap-2">
      <span className="w-12 shrink-0 text-[10px] font-semibold uppercase tracking-[0.08em] text-foreground-muted">
        {label}
      </span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-border/50">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${widthPct}%` }} />
      </div>
      <span className="w-14 shrink-0 text-right text-xs font-semibold tabular-nums text-foreground">
        {value.toFixed(2)}
      </span>
    </div>
  );
}
