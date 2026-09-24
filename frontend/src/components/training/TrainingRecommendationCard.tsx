"use client";

/**
 * Just-in-time training recommendation. Presentation only — the reason and
 * priority are supplied by lib/api.ts (mock now, `training_recommendation`
 * WS event or GET /training/recommendations/{operator_id} later); this
 * component never calculates a recommendation itself.
 *
 * Reused on Active Task ("surface a recommendation when appropriate") and on
 * the Training Hub's "Recommended for you" — same data shape, same card.
 */
import { useState } from "react";

import { api } from "@/lib/api";
import type { TrainingRecommendation } from "@/types";

import { CloseIcon } from "../common/icons";
import { Button, Card } from "../common/ui";

interface TrainingRecommendationCardProps {
  recommendation: TrainingRecommendation;
  /** Active Task shows a dismiss control; Training Hub's own section does not need one. */
  dismissible?: boolean;
}

export function TrainingRecommendationCard({ recommendation, dismissible = true }: TrainingRecommendationCardProps) {
  const [dismissed, setDismissed] = useState(false);
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle");
  if (dismissed) return null;

  const watch = () => {
    setStatus("saving");
    api
      .completeTraining(recommendation.clipId)
      .then(() => setStatus("done"))
      .catch(() => setStatus("error"));
  };

  return (
    <Card rounded="lg" className="border-brand-500/40" data-testid="training-recommendation">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-brand-600">Recommended {dismissible ? "now" : "for you"}</p>
        {dismissible && (
          <button
            onClick={() => setDismissed(true)}
            aria-label="Dismiss training recommendation"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-industrial text-foreground-muted hover:text-foreground"
          >
            <CloseIcon className="h-4 w-4" aria-hidden />
          </button>
        )}
      </div>
      <h3 className="mt-1 font-display text-xl font-semibold tracking-tight text-foreground">{recommendation.title}</h3>
      <p className="mt-1 text-sm font-medium text-foreground-muted">Why: {recommendation.reason}</p>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">
          {status === "error" ? "Couldn't save — try again" : `${recommendation.durationMin} min`}
        </span>
        <Button variant="primary" onClick={watch} disabled={status === "saving" || status === "done"}>
          {status === "done" ? "Watched" : status === "saving" ? "Saving…" : dismissible ? "Watch Now" : "Watch Clip"}
        </Button>
      </div>
    </Card>
  );
}
