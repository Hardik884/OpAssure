"use client";

/**
 * The reusable representation of "who / what / which task / how safe" that the
 * header, navigation badges, and every screen read from — instead of each
 * component fetching or hard-coding operator/machine identity separately.
 *
 * Populated from mock data for this foundation prompt (lib/api.ts). Later
 * prompts can refresh this from the real backend / WebSocket without changing
 * how consumers read it via `useOperatorContext()`.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api, errorMessage } from "@/lib/api";
import { mockOperatorContext } from "@/lib/mockData";
import type { OperatorContext, SafetyStatus } from "@/types";

interface OperatorContextValue {
  context: OperatorContext;
  loading: boolean;
  error: string | null;
  /** Lets a screen (e.g. Active Task's demo proximity alert) update the app-wide safety chip. */
  setSafetyStatus: (status: SafetyStatus) => void;
}

const Context = createContext<OperatorContextValue | null>(null);

export function OperatorProvider({ children }: { children: ReactNode }) {
  // Seeded with mock data immediately so the shell never renders empty on first paint.
  const [context, setContext] = useState<OperatorContext>(mockOperatorContext);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getOperatorContext()
      .then((result) => {
        if (!cancelled) setContext(result);
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

  const setSafetyStatus = (status: SafetyStatus) => setContext((prev) => ({ ...prev, safetyStatus: status }));

  return <Context.Provider value={{ context, loading, error, setSafetyStatus }}>{children}</Context.Provider>;
}

export function useOperatorContext(): OperatorContextValue {
  const value = useContext(Context);
  if (!value) throw new Error("useOperatorContext must be used within OperatorProvider");
  return value;
}
