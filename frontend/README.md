# OpAssure — Frontend

**Owner:** Frontend developer
**Stack:** Next.js (App Router), React, TypeScript, Tailwind CSS

> Status: complete — Mission Board, Active Task, Safety, Incident reporting,
> Training Hub, Operator Twin/Insights, History, PWA/offline support, and
> realtime WS integration are all built, and **wired to the real backend +
> ML layer** (`lib/api.ts` maps every function to a real endpoint — see
> docs/api/README.md and ml/docs/integration.md). `NEXT_PUBLIC_USE_MOCK_DATA=true`
> still renders the whole app from mock data for UI-only work with no backend running.

## Design language

Industrial, high-contrast, operator-first — not a generic analytics dashboard.
Palette is intentionally restricted:

- **Yellow** (`brand-*`) — accent / primary action only.
- **Black** (`ink-*`) — dark surfaces, navigation, strong text.
- **White** — primary content surfaces.
- **Gray** (`line-*`) — secondary surfaces, borders, metadata.
- **Green / amber / red** (`safe-*` / `warn-*` / `critical-*`) — status **only**,
  never decorative. Every status indicator pairs color with an icon and a word.

Tokens live in `src/app/globals.css` (`@theme`); primitives (Card, Button,
StatusBadge, MetricDisplay, ...) live in `src/components/common/ui.tsx`.

## Structure

| Path                          | Purpose                                                                 |
| ------------------------------ | ----------------------------------------------------------------------- |
| `src/app/layout.tsx`           | Root layout — wraps every route in `AppShell`.                          |
| `src/app/page.tsx`             | Shell landing view (operator/machine/task snapshot).                    |
| `src/app/mission/`             | Daily task dashboard (Mission Board) route — placeholder.               |
| `src/app/task/`                | Active task view route — placeholder.                                   |
| `src/app/safety/`              | Safety alerts route — placeholder.                                      |
| `src/app/training/`            | Operator training route — placeholder.                                  |
| `src/app/insights/`            | Insights (Operator Twin, ETA, performance) route — placeholder.         |
| `src/app/history/`             | Past shifts / task history route — placeholder.                        |
| `src/components/layout/`       | `AppShell`, `Header`, `Nav`, `OperatorProvider` (shared operator/machine/task/safety context). |
| `src/components/common/`       | Design system primitives (`ui.tsx`) and nav icons (`icons.tsx`).        |
| `src/components/<feature>/`    | Feature-specific components land here (empty until their prompt).       |
| `src/hooks/`                   | `useTask`, `useSafety`, `useTelemetry` — currently mock-backed.         |
| `src/lib/api.ts`                | The one place HTTP calls to the backend are made (mock/real switch via `USE_MOCK_DATA`). |
| `src/lib/websocket.ts`         | WS event types + a minimal connection wrapper (no reconnect logic yet). |
| `src/lib/mockData.ts`          | Demo fixtures for OP1001 / EXC001 / T001.                               |
| `src/types/index.ts`           | Frozen domain contract types (`Task`, `SafetyEvent`, `OperatorInsight`, ...) — do not rename these fields. |
| `src/config/`                  | `env.ts` (backend URLs, mock-data flag), `demo.ts` (shared demo IDs).   |
| `public/icons/`, `public/training/` | Static assets.                                                    |

## Local development

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
npm run build     # production build
npm run lint       # ESLint (flat config, eslint-config-next)
npm run typecheck  # tsc --noEmit
```

## Environment

Uses `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`), `NEXT_PUBLIC_WS_URL`
(default `ws://localhost:8000/ws`), and `NEXT_PUBLIC_USE_MOCK_DATA`. `next.config.ts`
reads these from `frontend/.env*` first, falling back to the repo-root `.env`
(see `.env.example`) so the whole monorepo can share one env file in local dev.

`src/config/env.ts` exports `USE_MOCK_DATA`: **real backend data by default**
(every `lib/api.ts` function calls the actual endpoint documented in
`docs/api/README.md` and maps its response onto the frozen types in `../types`
— no component ever sees a raw backend field name). Set
`NEXT_PUBLIC_USE_MOCK_DATA=true` to render `lib/mockData.ts` instead, for
UI-only work with no backend/database running; it's also the automatic
fallback if `NEXT_PUBLIC_API_URL` is unset. No component changes are needed
either way.

Real-mode notes:
- Everything is scoped to the single demo identity (`OP1001`/`EXC001`,
  `config/demo.ts`) — this app has no operator switcher.
- Mission Board rows use each task's own plan estimate (not a per-row ML
  call); only the active/current task gets a live personalized ETA range
  from `GET /insights/operator/{id}/ml` — see that endpoint's docs for why.
- `ApproxTrucksRemaining` shows the real buckets-remaining count when no
  truck-capacity figure exists (the ML layer never fabricates one) — the
  accompanying `etaReasons` text says so explicitly.
