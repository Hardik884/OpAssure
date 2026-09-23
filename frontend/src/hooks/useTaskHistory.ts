"use client";

/** Today's completed activity for /history. Reads through lib/api.ts. */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { HistoryEntry } from "@/types";

interface UseTaskHistoryResult {
  entries: HistoryEntry[];
  loading: boolean;
  error: string | null;
}

export function useTaskHistory(): UseTaskHistoryResult {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getTaskHistory()
      .then((result) => {
        if (!cancelled) setEntries(result);
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

  return { entries, loading, error };
}
