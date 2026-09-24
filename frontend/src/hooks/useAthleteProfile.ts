"use client";

/** Athlete Card data for the Insights page. Reads through lib/api.ts — the
 * frontend never computes or adjusts any of these numbers. */
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import type { AthleteProfile } from "@/types";

interface UseAthleteProfileResult {
  profile: AthleteProfile | null;
  loading: boolean;
  error: string | null;
}

export function useAthleteProfile(): UseAthleteProfileResult {
  const [profile, setProfile] = useState<AthleteProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getAthleteProfile()
      .then((result) => {
        if (!cancelled) setProfile(result);
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

  return { profile, loading, error };
}
