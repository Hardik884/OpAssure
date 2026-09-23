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
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Metric label="Pace" value={twin.paceFactor.toFixed(2)} />
        <Metric label="Rain sensitivity" value={twin.rainSensitivity.toFixed(2)} />
        <Metric label="Pattern" value={capitalize(twin.fatiguePattern)} />
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-widest text-foreground-muted">{label}</p>
      <p className="text-xl font-black leading-tight text-foreground sm:text-2xl">{value}</p>
    </div>
  );
}

function capitalize(value: string): string {
  return value.length === 0 ? value : value[0].toUpperCase() + value.slice(1);
}
