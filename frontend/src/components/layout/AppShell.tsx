"use client";

/**
 * The operator application shell: header, navigation, and the main content
 * region every route renders into. Wraps children in OperatorProvider so
 * operator/machine/task/safety context is available anywhere below it.
 */
import type { ReactNode } from "react";

import { Header } from "./Header";
import { Nav } from "./Nav";
import { OperatorProvider } from "./OperatorProvider";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <OperatorProvider>
      <div className="min-h-screen bg-line-100">
        <Header />
        <Nav />
        {/* pb-20 clears the fixed bottom tab bar on phone widths (sm:pb-0 removes it back). */}
        <main className="pb-20 sm:pb-0">{children}</main>
      </div>
    </OperatorProvider>
  );
}
