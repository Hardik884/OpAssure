"use client";

/**
 * Insights page data: Operator Twin, Habit Radar, Focus. Reads through
 * lib/api.ts (mock data for now) — the frontend never interprets or derives
 * these values, only renders what's supplied.
 */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { FocusItem, HabitRadarItem, OperatorInsight } from "@/types";

interface UseInsightsResult {
  twin: OperatorInsight | null;
  habits: HabitRadarItem[];
  focus: FocusItem[];
  loading: boolean;
  error: string | null;
}

export function useInsights(): UseInsightsResult {
  const [twin, setTwin] = useState<OperatorInsight | null>(null);
  const [habits, setHabits] = useState<HabitRadarItem[]>([]);
  const [focus, setFocus] = useState<FocusItem[]>([]);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getOperatorInsight(), api.getHabitRadar(), api.getFocus()])
      .then(([twinResult, habitResult, focusResult]) => {
        if (!cancelled) {
          setTwin(twinResult);
          setHabits(habitResult);
          setFocus(focusResult);
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

  return { twin, habits, focus, loading, error };
}
