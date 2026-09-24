/**
 * The Athlete Card — literalizes CLAUDE.md's central idea ("treat every
 * operator like a professional athlete") as a visual identity instead of a
 * plain metrics grid. Every stat is the Operator Twin's own number, presented
 * as-is (no interpretation, no invented rating) — see OperatorInsight/CLAUDE.md
 * §1 principle 5.
 */
import { riskToStatus } from "@/lib/format";
import type { AthleteProfile } from "@/types";

import { Card, StatusBadge } from "../common/ui";

/** OP1001 -> "01" — the trailing digits read as a jersey number, nothing computed. */
function jerseyNumber(operatorId: string): string {
  const digits = operatorId.replace(/\D/g, "");
  return digits.slice(-2).padStart(2, "0");
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "OP";
}

export function AthleteCard({ profile }: { profile: AthleteProfile }) {
  return (
    <Card rounded="lg" tone="dark" className="border-brand-500" data-testid="athlete-card">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-industrial border-2 border-brand-500 bg-ink-950 text-lg font-black text-brand-500">
            {initials(profile.name)}
          </span>
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-white/60">
              {profile.skill} &middot; {profile.machineType} Operator
            </p>
            <h3 className="text-xl font-black uppercase tracking-tight text-white sm:text-2xl">{profile.name}</h3>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="text-3xl font-black leading-none text-brand-500">#{jerseyNumber(profile.operatorId)}</span>
          <StatusBadge status={riskToStatus(profile.riskLevel)}>{profile.riskLevel} risk</StatusBadge>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3 border-t-2 border-white/10 pt-4 sm:grid-cols-6">
        <Stat label="Pace" value={profile.paceFactor.toFixed(2)} />
        <Stat label="Tasks logged" value={String(profile.gamesPlayed)} />
        <Stat label="Rain sensitivity" value={profile.rainSensitivity.toFixed(2)} />
        <Stat label="Heat sensitivity" value={profile.heatSensitivity.toFixed(2)} />
        <Stat label="Fuel efficiency" value={`${profile.fuelEfficiency.toFixed(2)}×`} />
        <Stat label="Seatbelt violation rate" value={`${Math.round(profile.seatbeltViolationRate * 100)}%`} />
      </div>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="truncate text-2xl font-black leading-none text-white sm:text-3xl">{value}</p>
      <p className="mt-1 text-[10px] font-bold uppercase leading-tight tracking-widest text-white/60">{label}</p>
    </div>
  );
}
