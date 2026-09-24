/**
 * The Athlete Card — literalizes CLAUDE.md's central idea ("treat every
 * operator like a professional athlete") as a visual identity instead of a
 * plain metrics grid. Every stat is the Operator Twin's own number, presented
 * as-is (no interpretation, no invented rating) — see OperatorInsight/CLAUDE.md
 * §1 principle 5.
 */
import { ClockIcon, FuelIcon, GaugeIcon, RainIcon, SeatbeltIcon, SunIcon } from "@/components/common/icons";
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
    <Card rounded="lg" tone="dark" data-testid="athlete-card">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-brand-500/50 bg-white/5 font-display text-lg font-semibold text-brand-500">
            {initials(profile.name)}
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-line-400">
              {profile.skill} &middot; {profile.machineType} Operator
            </p>
            <h3 className="font-display text-xl font-semibold tracking-tight text-white sm:text-2xl">{profile.name}</h3>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="font-display text-3xl font-semibold leading-none text-brand-500">
            #{jerseyNumber(profile.operatorId)}
          </span>
          <StatusBadge status={riskToStatus(profile.riskLevel)}>{profile.riskLevel} risk</StatusBadge>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-4 border-t border-white/10 pt-4 sm:grid-cols-6">
        <Stat icon={GaugeIcon} label="Pace" value={profile.paceFactor.toFixed(2)} />
        <Stat icon={ClockIcon} label="Tasks logged" value={String(profile.gamesPlayed)} />
        <Stat icon={RainIcon} label="Rain sensitivity" value={profile.rainSensitivity.toFixed(2)} />
        <Stat icon={SunIcon} label="Heat sensitivity" value={profile.heatSensitivity.toFixed(2)} />
        <Stat icon={FuelIcon} label="Fuel efficiency" value={`${profile.fuelEfficiency.toFixed(2)}×`} />
        <Stat icon={SeatbeltIcon} label="Seatbelt violation rate" value={`${Math.round(profile.seatbeltViolationRate * 100)}%`} />
      </div>
    </Card>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof GaugeIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0">
      <Icon className="h-4 w-4 text-line-400" aria-hidden />
      <p className="mt-1 truncate font-display text-xl font-semibold leading-none text-white sm:text-2xl">{value}</p>
      <p className="mt-1 text-[10px] font-semibold uppercase leading-tight tracking-[0.08em] text-line-400">{label}</p>
    </div>
  );
}
