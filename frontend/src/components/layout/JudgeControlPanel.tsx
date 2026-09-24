"use client";

/**
 * Judge Control Panel — a hidden-in-plain-sight admin tool, not an operator
 * feature. Lets anyone in the room (a hackathon judge) trigger a real event —
 * a worker intrusion, a rainstorm, a cycle-time spike — and watch ETA, risk
 * and safety alerts update live across the app via the real WebSocket
 * pipeline (see backend/app/api/judge.py). Every number that changes comes
 * from the backend's real rule engine/ETA function; this panel only supplies
 * the trigger, never the resulting numbers.
 *
 * Only rendered/usable while genuinely connected to a live backend
 * (connectionMode === "live") — it has nothing to do while running on mock
 * data, and never pretends to.
 */
import { useState } from "react";

import { PlayIcon, ProximityIcon, RefreshIcon, SlidersIcon, StormIcon, GaugeIcon } from "@/components/common/icons";
import { useRealtime } from "@/components/layout/RealtimeProvider";
import { api, errorMessage } from "@/lib/api";

import { Button } from "../common/ui";
import { Modal } from "../common/Modal";

type ActionKey = "proximity" | "rain" | "cycle" | "reset" | "start";

export function JudgeControlPanel() {
  const { connectionMode } = useRealtime();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState<ActionKey | null>(null);
  const [note, setNote] = useState<string | null>(null);

  if (connectionMode !== "live") return null;

  const run = (key: ActionKey, action: () => Promise<{ triggered?: boolean; started?: boolean }>, label: string) => {
    setPending(key);
    setNote(null);
    action()
      .then((result) => {
        const ok = result.triggered ?? result.started ?? false;
        setNote(ok ? `${label} — watch Task/Insights update.` : `${label}: nothing changed (is the replay running?)`);
      })
      .catch((err) => setNote(errorMessage(err)))
      .finally(() => setPending(null));
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="Open Judge Control Panel"
        className="fixed bottom-24 right-4 z-30 flex h-14 w-14 items-center justify-center rounded-full border border-brand-500/50 bg-ink-950 text-brand-500 shadow-lg transition-colors hover:bg-ink-800 sm:bottom-6"
      >
        <SlidersIcon className="h-6 w-6" aria-hidden />
      </button>

      {open && (
        <Modal title="Judge Control Panel" onClose={() => setOpen(false)}>
          <p className="mb-4 text-sm font-medium text-foreground-muted">
            Trigger a real event and watch it propagate live — ETA, risk and safety alerts all update through the
            same pipeline real telemetry uses. Nothing here is faked.
          </p>

          <div className="space-y-3">
            <PanelButton
              icon={PlayIcon}
              busy={pending === "start"}
              onClick={() => run("start", () => api.startDemoReplay(), "Replay started")}
            >
              Start Replay
            </PanelButton>
            <PanelButton
              icon={ProximityIcon}
              busy={pending === "proximity"}
              onClick={() => run("proximity", () => api.triggerProximityIntrusion(), "Proximity intrusion triggered")}
            >
              Trigger Proximity Intrusion
            </PanelButton>
            <PanelButton
              icon={StormIcon}
              busy={pending === "rain"}
              onClick={() => run("rain", () => api.triggerRainstorm(), "Rainstorm dropped")}
            >
              Drop Rainstorm
            </PanelButton>
            <PanelButton
              icon={GaugeIcon}
              busy={pending === "cycle"}
              onClick={() => run("cycle", () => api.triggerCycleSpike(), "Cycle-time spike triggered")}
            >
              Spike Cycle Time
            </PanelButton>
            <PanelButton
              icon={RefreshIcon}
              busy={pending === "reset"}
              onClick={() => run("reset", () => api.resetJudgeOverrides(), "Reset to normal")}
            >
              Reset to Normal
            </PanelButton>
          </div>

          {note && (
            <p className="mt-4 text-sm font-semibold text-foreground" role="status">
              {note}
            </p>
          )}
        </Modal>
      )}
    </>
  );
}

function PanelButton({
  icon: Icon,
  children,
  busy,
  onClick,
}: {
  icon: typeof PlayIcon;
  children: string;
  busy: boolean;
  onClick: () => void;
}) {
  return (
    <Button variant="secondary" className="flex w-full items-center gap-3 text-left" disabled={busy} onClick={onClick}>
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      {busy ? "Working…" : children}
    </Button>
  );
}
