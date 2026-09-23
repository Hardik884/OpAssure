/**
 * Design system primitives — the industrial CAT-style language shared by every
 * screen. Deliberately flatter and higher-contrast than a generic SaaS dashboard:
 * square-ish corners, bold borders, solid status blocks, uppercase labels.
 *
 * Status color is a functional signal only (green=safe, amber=warning,
 * red=critical) — every status badge/indicator also carries an icon and a word,
 * never color alone.
 */
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

import type { SafetyStatus } from "@/types";

/* ---------------------------------------------------------------- layout ---- */

/** Page-level container: consistent max width + gutters at every breakpoint. */
export function PageContainer({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`mx-auto w-full max-w-6xl px-4 py-4 sm:px-6 sm:py-6 ${className}`}>{children}</div>;
}

/** A bordered content surface. Flat, not a floating rounded-2xl card. */
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
  /** "sm" (default, existing sharp/industrial radius) or "lg" for hero surfaces (ETA card, modals). */
  rounded?: "sm" | "lg";
  /** "light" (default, white/ink-on-white) or "dark" (ink surface/white text) for a hero panel like Active Task's ETA card. */
  tone?: "light" | "dark";
} & HTMLAttributes<HTMLElement>) {
  const radius = rounded === "lg" ? "rounded-panel" : "rounded-industrial";
  const surface = tone === "dark" ? "border-ink-950 bg-ink-950 text-white" : "border-ink-950 bg-white text-ink-950";
  return (
    <section {...rest} className={`${radius} border-2 ${surface} ${padded ? "p-4 sm:p-5" : ""} ${className}`}>
      {children}
    </section>
  );
}

/** Uppercase, tracked-out label used above every section — instrument-panel feel. */
export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3 border-b-2 border-ink-950 pb-2">
      <h2 className="text-xs font-bold uppercase tracking-widest text-ink-700">{title}</h2>
      {action}
    </div>
  );
}

/* ---------------------------------------------------------------- status ---- */

const STATUS_STYLE: Record<SafetyStatus, { bg: string; fg: string; icon: string; label: string }> = {
  safe: { bg: "bg-safe-bg", fg: "text-safe-600", icon: "✓", label: "Safe" },
  warning: { bg: "bg-warn-bg", fg: "text-warn-600", icon: "⚠", label: "Warning" },
  critical: { bg: "bg-critical-bg", fg: "text-critical-600", icon: "⛔", label: "Critical" },
};

/** Solid status block: icon + word, never color alone (accessibility). */
export function StatusBadge({ status, children }: { status: SafetyStatus; children?: ReactNode }) {
  const s = STATUS_STYLE[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-industrial px-2.5 py-1 text-sm font-bold ${s.bg} ${s.fg}`}
    >
      <span aria-hidden>{s.icon}</span>
      {children ?? s.label}
    </span>
  );
}

/** Small filled dot + label for compact contexts (header chips, list rows). */
export function StatusDot({ status, label }: { status: SafetyStatus; label: string }) {
  const dotColor = status === "safe" ? "bg-safe-500" : status === "warning" ? "bg-warn-500" : "bg-critical-500";
  return (
    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-900">
      <span className={`h-2.5 w-2.5 rounded-full ${dotColor}`} aria-hidden />
      {label}
    </span>
  );
}

/* ---------------------------------------------------------------- controls -- */

type ButtonVariant = "primary" | "secondary" | "ghost";

const BUTTON_VARIANT: Record<ButtonVariant, string> = {
  primary: "bg-brand-500 text-ink-950 border-2 border-ink-950 hover:bg-brand-400 active:bg-brand-600",
  secondary: "bg-ink-950 text-white border-2 border-ink-950 hover:bg-ink-800 active:bg-ink-700",
  ghost: "bg-transparent text-ink-950 border-2 border-line-300 hover:border-ink-950",
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
      className={`min-h-12 rounded-industrial px-5 text-base font-bold uppercase tracking-wide transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${BUTTON_VARIANT[variant]} ${className}`}
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
      <div className="text-xs font-bold uppercase tracking-widest text-ink-600">{label}</div>
      <div className="text-4xl font-black tabular-nums leading-none text-ink-950 sm:text-5xl">
        {value}
        {unit && <span className="ml-2 text-lg font-bold text-ink-600">{unit}</span>}
      </div>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm font-medium text-line-500">{children}</p>;
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-industrial border-2 border-critical-500 bg-critical-bg px-3 py-2 text-sm font-semibold text-critical-600">
      ⚠ {children}
    </p>
  );
}

export function VisuallyHidden(props: HTMLAttributes<HTMLSpanElement>) {
  return <span className="sr-only" {...props} />;
}
