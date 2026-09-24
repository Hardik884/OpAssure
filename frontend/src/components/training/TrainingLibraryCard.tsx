"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import type { TrainingClip } from "@/types";

import { Button, Card } from "../common/ui";

export function TrainingLibraryCard({ clip }: { clip: TrainingClip }) {
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle");

  const watch = () => {
    setStatus("saving");
    api
      .completeTraining(clip.clipId)
      .then(() => setStatus("done"))
      .catch(() => setStatus("error"));
  };

  return (
    <Card>
      <p className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">{clip.category}</p>
      <h3 className="mt-1 font-display text-lg font-semibold tracking-tight text-foreground">{clip.title}</h3>
      <p className="mt-1 text-sm font-medium text-foreground-muted">{clip.description}</p>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">
          {status === "error" ? "Couldn't save — try again" : `${clip.durationMin} min`}
        </span>
        <Button variant="secondary" onClick={watch} disabled={status === "saving" || status === "done"}>
          {status === "done" ? "Watched" : status === "saving" ? "Saving…" : "Watch"}
        </Button>
      </div>
    </Card>
  );
}
