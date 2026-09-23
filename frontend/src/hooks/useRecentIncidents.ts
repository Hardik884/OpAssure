"use client";

/** Recent incidents for the /safety page. Reads through lib/api.ts. */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { Incident } from "@/types";

interface UseRecentIncidentsResult {
  incidents: Incident[];
  loading: boolean;
  error: string | null;
}

export function useRecentIncidents(): UseRecentIncidentsResult {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getRecentIncidents()
      .then((result) => {
        if (!cancelled) setIncidents(result);
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

  return { incidents, loading, error };
}
