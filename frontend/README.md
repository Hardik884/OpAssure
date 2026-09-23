# OpAssure — Frontend

**Owner:** Frontend developer
**Stack:** Next.js (App Router), React, TypeScript, Tailwind CSS

> Status: application shell + design system foundation in place (this is the
> operator-facing PWA shell — header, navigation, industrial CAT-style design
> tokens, mock data layer, typed API/WebSocket client scaffolding). Mission
> Board, Active Task, Safety event flows, Incident form, Training Hub and
> Operator Twin views are placeholder routes, built out in later work.

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

Uses `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`. `next.config.ts` reads
these from `frontend/.env*` first, falling back to the repo-root `.env` (see
`.env.example`) so the whole monorepo can share one env file in local dev.

`src/config/env.ts` also exports `USE_MOCK_DATA` (currently `true`): every
`lib/api.ts` function returns mock data from `lib/mockData.ts` under this flag
and switches to a real `fetch` call against the backend when it's flipped —
no component changes required either way.
