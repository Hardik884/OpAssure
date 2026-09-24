/**
 * Operator Twin summary — presents the frozen OperatorInsight contract
 * exactly as supplied. No interpretation beyond the data (no medical or
 * psychological claims) — see CLAUDE.md/handover.
 */
import { riskToStatus } from "@/lib/format";
import type { OperatorInsight } from "@/types";

import { Card, SectionHeader, StatusBadge } from "../common/ui";

export function OperatorTwinCard({ twin }: { twin: OperatorInsight }) {
  return (
    <Card rounded="lg">
      <SectionHeader title="Operator Twin" action={<StatusBadge status={riskToStatus(twin.riskLevel)}>{twin.riskLevel} risk</StatusBadge>} />
      <div className="grid grid-cols-2 gap-4">
        <Metric label="Pace" value={twin.paceFactor.toFixed(2)} />
        <Metric label="Rain sensitivity" value={twin.rainSensitivity.toFixed(2)} />
      </div>
      <div className="mt-4">
        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">Pattern</p>
        <p className="mt-1 text-sm font-medium leading-snug text-foreground">{capitalize(twin.fatiguePattern)}</p>
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">{label}</p>
      <p className="font-display truncate text-xl font-semibold leading-tight text-foreground sm:text-2xl">{value}</p>
    </div>
  );
}

function capitalize(value: string): string {
  return value.length === 0 ? value : value[0].toUpperCase() + value.slice(1);
}
