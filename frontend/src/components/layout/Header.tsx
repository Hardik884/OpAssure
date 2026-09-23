"use client";

/**
 * App header: branding + who's in the cab + what they're driving + a one-glance
 * safety chip. Dark industrial surface (ink), brand yellow accent only on the
 * wordmark — yellow stays an accent, never a background wash.
 */
import { StatusBadge } from "@/components/common/ui";

import { useOperatorContext } from "./OperatorProvider";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  const { context } = useOperatorContext();
  const { operator, machine, safetyStatus } = context;

  return (
    <header className="sticky top-0 z-30 border-b-2 border-ink-950 bg-ink-950 text-white">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-2">
          <span className="shrink-0 rounded-industrial bg-brand-500 px-2 py-1 text-sm font-black tracking-tight text-ink-950">
            OP
          </span>
          <span className="truncate text-lg font-extrabold tracking-tight">OpAssure</span>
        </div>

        <div className="flex min-w-0 items-center gap-4">
          <div className="hidden text-right sm:block">
            <div className="text-sm font-bold leading-tight">{operator.name}</div>
            <div className="text-xs leading-tight text-line-400">{operator.operatorId}</div>
          </div>
          <div className="hidden text-right md:block">
            <div className="text-sm font-bold leading-tight">{machine.machineId}</div>
            <div className="text-xs leading-tight text-line-400">{machine.model}</div>
          </div>
          <StatusBadge status={safetyStatus} />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
