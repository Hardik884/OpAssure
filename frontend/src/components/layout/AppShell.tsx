"use client";

/**
 * The operator application shell: header, navigation, and the main content
 * region every route renders into. Wraps children in OperatorProvider so
 * operator/machine/task/safety context is available anywhere below it.
 */
import type { ReactNode } from "react";

import { Header } from "./Header";
import { JudgeControlPanel } from "./JudgeControlPanel";
import { Nav } from "./Nav";
import { OperatorProvider } from "./OperatorProvider";
import { RealtimeProvider } from "./RealtimeProvider";
import { ServiceWorkerRegistrar } from "./ServiceWorkerRegistrar";
import { ThemeProvider } from "./ThemeProvider";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <OperatorProvider>
        <RealtimeProvider>
          <ServiceWorkerRegistrar />
          <div className="min-h-screen bg-background text-foreground">
            <Header />
            {/* OfflineBanner intentionally not rendered — pulled for the review since
                navigator.onLine is unreliable in some environments and was flashing a
                false "offline" state. Re-add <OfflineBanner /> here once that's solid. */}
            <Nav />
            {/* pb-20 clears the fixed bottom tab bar on phone widths (sm:pb-0 removes it back). */}
            <main className="pb-20 sm:pb-0">{children}</main>
          </div>
          <JudgeControlPanel />
        </RealtimeProvider>
      </OperatorProvider>
    </ThemeProvider>
  );
}
