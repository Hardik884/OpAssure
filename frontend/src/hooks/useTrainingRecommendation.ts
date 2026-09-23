"use client";

/**
 * The current just-in-time training recommendation (Active Task's
 * TrainingRecommendation card, and Training Hub's "Recommended for you").
 * Reads through lib/api.ts — never computed here. Prepared for a future WS
 * `training_recommendation` event to override this without a reload.
 */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { TrainingRecommendation } from "@/types";

interface UseTrainingRecommendationResult {
  recommendation: TrainingRecommendation | null;
  loading: boolean;
  error: string | null;
}

export function useTrainingRecommendation(): UseTrainingRecommendationResult {
  const [recommendation, setRecommendation] = useState<TrainingRecommendation | null>(null);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getTrainingRecommendation()
      .then((result) => {
        if (!cancelled) setRecommendation(result);
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

  return { recommendation, loading, error };
}
