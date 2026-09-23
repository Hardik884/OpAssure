"use client";

/**
 * Supplementary Active Task facts (why the ETA moved, the truck estimate).
 * Reads through lib/api.ts (mock data for now) — never computed here.
 */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { ActiveTaskInsight } from "@/types";

interface UseActiveTaskInsightResult {
  insight: ActiveTaskInsight | null;
  loading: boolean;
  error: string | null;
}

export function useActiveTaskInsight(taskId: string | undefined): UseActiveTaskInsightResult {
  const [insight, setInsight] = useState<ActiveTaskInsight | null>(null);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return; // stay in the initial loading state until the task itself has loaded
    let cancelled = false;
    api
      .getActiveTaskInsight(taskId)
      .then((result) => {
        if (!cancelled) setInsight(result);
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
  }, [taskId]);

  return { insight, loading, error };
}
