/**
 * Minimal inline stroke icons — no icon library dependency. 24x24, stroke-based,
 * currentColor so every icon inherits its surrounding text/status color.
 * Used everywhere a unicode glyph or emoji would otherwise stand in (status,
 * weather, safety rows) — see CLAUDE.md §12 (icon + text, never color alone).
 */
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const base = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

/* ---------------------------------------------------------------- nav ------ */

export function MissionIcon(props: IconProps) {
  return (
    <svg {...base} strokeWidth={2} {...props}>
      <rect x="4" y="3" width="16" height="18" rx="1" />
      <path d="M9 3v2h6V3M8 9h8M8 13h8M8 17h5" />
    </svg>
  );
}

export function TaskIcon(props: IconProps) {
  return (
    <svg {...base} strokeWidth={2} {...props}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export function SafetyIcon(props: IconProps) {
  return (
    <svg {...base} strokeWidth={2} {...props}>
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
    </svg>
  );
}

export function TrainingIcon(props: IconProps) {
  return (
    <svg {...base} strokeWidth={2} {...props}>
      <path d="M3 6l9-3 9 3-9 3-9-3z" />
      <path d="M7 9.5V15c0 1.5 2.5 3 5 3s5-1.5 5-3V9.5" />
    </svg>
  );
}

export function InsightsIcon(props: IconProps) {
  return (
    <svg {...base} strokeWidth={2} {...props}>
      <path d="M4 19V5M4 19h16" />
      <path d="M8 15l3-4 3 2 4-6" />
    </svg>
  );
}

export function HistoryIcon(props: IconProps) {
  return (
    <svg {...base} strokeWidth={2} {...props}>
      <circle cx="12" cy="13" r="8" />
      <path d="M12 9v4l3 2" />
      <path d="M9 2h6" />
    </svg>
  );
}

/* ------------------------------------------------------------- status ------ */

export function CheckIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M5 13l4 4L19 7" />
    </svg>
  );
}

export function AlertTriangleIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3.5l9 15.5H3l9-15.5z" />
      <path d="M12 10v4" />
      <circle cx="12" cy="17" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function AlertOctagonIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M8 3h8l5 5v8l-5 5H8l-5-5V8l5-5z" />
      <path d="M12 8v5" />
      <circle cx="12" cy="16.5" r="0.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

/* ------------------------------------------------------------- safety ------ */

export function SeatbeltIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
      <path d="M9 12.2l2 2 4.2-4.6" />
    </svg>
  );
}

export function ProximityIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="2.2" />
      <path d="M8.2 8.2a5.4 5.4 0 000 7.6M15.8 8.2a5.4 5.4 0 010 7.6" />
      <path d="M5 5a10 10 0 000 14M19 5a10 10 0 010 14" />
    </svg>
  );
}

export function MachineIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M3 16.5h6l2-4h4.5l2.5 4H21" />
      <circle cx="7" cy="18.5" r="1.8" />
      <circle cx="17" cy="18.5" r="1.8" />
      <path d="M11 12.5V7h3l3 3.5" />
    </svg>
  );
}

/* ------------------------------------------------------------- weather ----- */

export function SunIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2.5M12 19v2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M2.5 12H5M19 12h2.5M4.6 19.4l1.8-1.8M17.6 6.4l1.8-1.8" />
    </svg>
  );
}

export function CloudIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M7 18a4.2 4.2 0 01-.6-8.36 5 5 0 019.6-1.5A4 4 0 0117 18H7z" />
    </svg>
  );
}

export function RainIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M7 15.2a4.2 4.2 0 01-.6-8.36 5 5 0 019.6-1.5A4 4 0 0117 13.2" />
      <path d="M8 17.5l-1 2.5M12 17.5l-1 2.5M16 17.5l-1 2.5" />
    </svg>
  );
}

export function StormIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M7 13.2a4.2 4.2 0 01-.6-8.36 5 5 0 019.6-1.5 4 4 0 01.9 7.86" />
      <path d="M13 13l-2.6 4.6H13L11 21" />
    </svg>
  );
}

/* -------------------------------------------------------------- misc ------- */

export function ClockIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  );
}

export function FuelIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3c4 5 6 8 6 11a6 6 0 11-12 0c0-3 2-6 6-11z" />
    </svg>
  );
}

export function GaugeIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 15a8 8 0 1116 0" />
      <path d="M12 15l4-5" />
    </svg>
  );
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

export function SunToggleIcon(props: IconProps) {
  return <SunIcon {...props} />;
}

export function MoonIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z" />
    </svg>
  );
}
