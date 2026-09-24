"use client";

/** Fleet-wide before/after training proof for the Insights page. Reads through
 * lib/api.ts — every number is a measured value from training_events, never
 * computed or projected in the UI. */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { TrainingImpactCase } from "@/types";

interface UseTrainingImpactResult {
  cases: TrainingImpactCase[];
  loading: boolean;
  error: string | null;
}

export function useTrainingImpact(): UseTrainingImpactResult {
  const [cases, setCases] = useState<TrainingImpactCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getTrainingImpact()
      .then((result) => {
        if (!cancelled) setCases(result);
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

  return { cases, loading, error };
}
