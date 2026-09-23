"use client";

/** Training Hub library + mock instructor slots. Reads through lib/api.ts. */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { InstructorSlot, TrainingClip } from "@/types";

interface UseTrainingLibraryResult {
  clips: TrainingClip[];
  slots: InstructorSlot[];
  loading: boolean;
  error: string | null;
}

export function useTrainingLibrary(): UseTrainingLibraryResult {
  const [clips, setClips] = useState<TrainingClip[]>([]);
  const [slots, setSlots] = useState<InstructorSlot[]>([]);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getTrainingLibrary(), api.getInstructorSlots()])
      .then(([clipResult, slotResult]) => {
        if (!cancelled) {
          setClips(clipResult);
          setSlots(slotResult);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { clips, slots, loading, error };
}
