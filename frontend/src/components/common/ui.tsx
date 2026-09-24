/**
 * Design system primitives — the industrial-modern language shared by every
 * screen: graphite/ivory surfaces, hairline borders, soft radii, amber +
 * signal-teal accents, Space Grotesk for headings and big numbers over
 * Manrope body text. Deliberately calm — no heavy black borders, no
 * shouting uppercase everywhere, no decorative gradients.
 *
 * Status color is a functional signal only (green=safe, amber=warning,
 * red=critical) — every status badge/indicator also carries an icon and a
 * word, never color alone.
 */
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

import type { SafetyStatus } from "@/types";

import { AlertOctagonIcon, AlertTriangleIcon, CheckIcon } from "./icons";

/* ---------------------------------------------------------------- layout ---- */

/** Page-level container: consistent max width + gutters at every breakpoint. */
export function PageContainer({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`mx-auto w-full max-w-6xl px-4 py-5 sm:px-6 sm:py-8 ${className}`}>{children}</div>;
}

/** Small eyebrow + heading used at the top of every route — replaces one-off h1s. */
export function PageTitle({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return (
    <div className="mb-5 flex items-end justify-between gap-3">
      <div>
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-[0.14em] text-foreground-muted">{eyebrow}</p>}
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">{title}</h1>
      </div>
      {action}
    </div>
  );
}

/** A bordered content surface — flat, hairline border, soft corners. Never a heavy boxed panel. */
export function Card({
  children,
  className = "",
  padded = true,
  rounded = "sm",
  tone = "light",
  ...rest
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
  /** "sm" (default, 12px) or "lg" (20px) for hero surfaces (ETA card, modals). */
  rounded?: "sm" | "lg";
  /** "light" (default) or "dark" — a graphite hero panel like Active Task's ETA card. */
  tone?: "light" | "dark";
} & HTMLAttributes<HTMLElement>) {
  const radius = rounded === "lg" ? "rounded-panel" : "rounded-industrial";
  const surface =
    tone === "dark"
      ? "border-white/10 bg-ink-900 text-white"
      : "border-border bg-surface text-foreground";
  return (
    <section {...rest} className={`${radius} border ${surface} ${padded ? "p-4 sm:p-5" : ""} ${className}`}>
      {children}
    </section>
  );
}

/** Small eyebrow label above a card section — quiet, not a heavy instrument-panel bar. */
export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-foreground-muted">{title}</h2>
      {action}
    </div>
  );
}

/* ---------------------------------------------------------------- status ---- */

const STATUS_STYLE: Record<SafetyStatus, { bg: string; fg: string; icon: typeof CheckIcon; label: string }> = {
  safe: { bg: "bg-status-safe-bg", fg: "text-status-safe-fg", icon: CheckIcon, label: "Safe" },
  warning: { bg: "bg-status-warn-bg", fg: "text-status-warn-fg", icon: AlertTriangleIcon, label: "Warning" },
  critical: { bg: "bg-status-critical-bg", fg: "text-status-critical-fg", icon: AlertOctagonIcon, label: "Critical" },
};

/** Pill status chip: icon + word, never color alone (accessibility). */
export function StatusBadge({ status, children }: { status: SafetyStatus; children?: ReactNode }) {
  const s = STATUS_STYLE[status];
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ${s.bg} ${s.fg}`}>
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
      {children ?? s.label}
    </span>
  );
}

/** Small filled dot + label for compact contexts (header chips, list rows). Optional live pulse. */
export function StatusDot({ status, label, pulse = false }: { status: SafetyStatus; label: string; pulse?: boolean }) {
  const dotColor = status === "safe" ? "bg-safe-500" : status === "warning" ? "bg-warn-500" : "bg-critical-500";
  return (
    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-foreground">
      <span className={`h-2 w-2 rounded-full ${dotColor} ${pulse ? "animate-live-pulse" : ""}`} aria-hidden />
      {label}
    </span>
  );
}

/* ---------------------------------------------------------------- controls -- */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_VARIANT: Record<ButtonVariant, string> = {
  primary: "bg-brand-500 text-ink-950 hover:bg-brand-400 active:bg-brand-600",
  secondary: "bg-ink-900 text-white hover:bg-ink-800 active:bg-ink-700",
  ghost: "bg-transparent text-foreground border border-border hover:border-line-400",
  danger: "bg-critical-500 text-white hover:brightness-105 active:brightness-95",
};

/** Every button is a large, glove-friendly touch target — never a small icon-only control. */
export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      {...props}
      className={`min-h-12 rounded-industrial px-5 text-[15px] font-semibold transition-colors duration-150 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 ${BUTTON_VARIANT[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

/* ---------------------------------------------------------------- metrics --- */

/** The large-number display used for ETA, distance, etc. — one glance, no reading. */
export function MetricDisplay({
  label,
  value,
  unit,
  className = "",
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="text-xs font-semibold uppercase tracking-[0.1em] text-foreground-muted">{label}</div>
      <div className="font-display text-4xl font-semibold tabular-nums leading-none text-foreground sm:text-5xl">
        {value}
        {unit && <span className="ml-2 text-lg font-medium text-foreground-muted">{unit}</span>}
      </div>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm font-medium text-foreground-muted">{children}</p>;
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p
      role="alert"
      className="flex items-start gap-2 rounded-industrial border border-critical-500/40 bg-status-critical-bg px-3 py-2 text-sm font-semibold text-status-critical-fg"
    >
      <AlertTriangleIcon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      {children}
    </p>
  );
}

export function VisuallyHidden(props: HTMLAttributes<HTMLSpanElement>) {
  return <span className="sr-only" {...props} />;
}
