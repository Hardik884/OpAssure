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
import type { OperatorContext } from "@/types";

interface OperatorContextValue {
  context: OperatorContext;
  loading: boolean;
  error: string | null;
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

  return <Context.Provider value={{ context, loading, error }}>{children}</Context.Provider>;
}

export function useOperatorContext(): OperatorContextValue {
  const value = useContext(Context);
  if (!value) throw new Error("useOperatorContext must be used within OperatorProvider");
  return value;
}
