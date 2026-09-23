"use client";

/**
 * The operator's current task. Reads through lib/api.ts (mock data for now).
 * The frontend never computes ETA/risk itself — it only displays what this
 * returns, which will be backend/AI-derived once the real API is wired in.
 */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { Task } from "@/types";

interface UseTaskResult {
  task: Task | null;
  loading: boolean;
  error: string | null;
}

export function useTask(): UseTaskResult {
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getCurrentTask()
      .then((result) => {
        if (!cancelled) setTask(result);
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

  return { task, loading, error };
}
