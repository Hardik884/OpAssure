"use client";

/**
 * Insights page data: Habit Radar, Focus. Reads through lib/api.ts (mock data
 * for now) — the frontend never interprets or derives these values, only
 * renders what's supplied. (Operator Twin now lives in useAthleteProfile.)
 */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { FocusItem, HabitRadarItem } from "@/types";

interface UseInsightsResult {
  habits: HabitRadarItem[];
  focus: FocusItem[];
  loading: boolean;
  error: string | null;
}

export function useInsights(): UseInsightsResult {
  const [habits, setHabits] = useState<HabitRadarItem[]>([]);
  const [focus, setFocus] = useState<FocusItem[]>([]);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getHabitRadar(), api.getFocus()])
      .then(([habitResult, focusResult]) => {
        if (!cancelled) {
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

  return { habits, focus, loading, error };
}
