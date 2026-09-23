"use client";

/**
 * Current safety events for the active machine. Reads through lib/api.ts (mock
 * data for now). Live updates via WS /ws `safety_alert`/`proximity_alert` events
 * are later work (lib/websocket.ts already defines the message shapes).
 */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { SafetyEvent } from "@/types";

interface UseSafetyResult {
  events: SafetyEvent[];
  loading: boolean;
  error: string | null;
}

export function useSafety(): UseSafetyResult {
  const [events, setEvents] = useState<SafetyEvent[]>([]);
  const [loading, setLoading] = useState(true); // already true on mount; effect only clears it
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getSafetyEvents()
      .then((result) => {
        if (!cancelled) setEvents(result);
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

  return { events, loading, error };
}
