"use client";

/**
 * Full-screen overlay used by Threat Briefing, task detail and the incident
 * flow. Bottom sheet on phone (thumb-reachable), centered dialog on tablet/
 * desktop — same flat/bordered panel language as Card, not a glassy popover.
 *
 * Kept out of ui.tsx (which plain server-component pages import) since this
 * component needs a client-only effect for the Escape key.
 */
import { useEffect, type ReactNode } from "react";

import { CloseIcon } from "./icons";

export function Modal({
  title,
  children,
  onClose,
  dismissible = true,
}: {
  title?: string;
  children: ReactNode;
  onClose?: () => void;
  /** false hides the close affordance — used where the operator must choose an action to proceed. */
  dismissible?: boolean;
}) {
  useEffect(() => {
    if (!dismissible || !onClose) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [dismissible, onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-40 flex items-end justify-center bg-ink-950/60 p-0 backdrop-blur-[2px] sm:items-center sm:p-4"
      onClick={dismissible ? onClose : undefined}
    >
      <div
        className="animate-rise-in max-h-[92vh] w-full overflow-y-auto rounded-t-panel border-t border-border bg-surface p-5 sm:max-w-lg sm:rounded-panel sm:border"
        onClick={(e) => e.stopPropagation()}
      >
        {(title || (dismissible && onClose)) && (
          <div className="mb-3 flex items-center justify-between gap-3">
            {title && <h2 className="font-display text-lg font-semibold tracking-tight text-foreground">{title}</h2>}
            {dismissible && onClose && (
              <button
                onClick={onClose}
                aria-label="Close"
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-industrial text-foreground-muted hover:bg-surface-muted hover:text-foreground"
              >
                <CloseIcon className="h-5 w-5" aria-hidden />
              </button>
            )}
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
