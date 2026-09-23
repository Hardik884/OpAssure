"use client";

/**
 * Today's Mission Board rows. Reads through lib/api.ts (mock data for now);
 * the eventual endpoint is GET /tasks/today?operator_id=OP1001.
 */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { MissionTask } from "@/types";

interface UseMissionTasksResult {
  tasks: MissionTask[];
  loading: boolean;
  error: string | null;
}

export function useMissionTasks(): UseMissionTasksResult {
  const [tasks, setTasks] = useState<MissionTask[]>([]);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getTodayTasks()
      .then((result) => {
        if (!cancelled) setTasks(result);
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

  return { tasks, loading, error };
}
