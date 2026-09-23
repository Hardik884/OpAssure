# OpAssure — Frontend

**Owner:** Frontend developer
**Stack:** Next.js, React, TypeScript

> Status: folder skeleton only. The Next.js project has not been scaffolded yet and no pages are implemented.

## Structure

| Path                 | Purpose                                              |
| -------------------- | ---------------------------------------------------- |
| `src/app/mission/`   | Daily task dashboard (mission board) route.          |
| `src/app/task/`      | Individual task view route.                          |
| `src/app/safety/`    | Safety alerts route.                                 |
| `src/app/training/`  | Operator training route.                             |
| `src/app/insights/`  | Insights (anomalies, ETA, performance) route.        |
| `src/app/history/`   | Past shifts / task history route.                    |
| `src/components/`    | UI components grouped by feature, plus `layout/` and `common/`. |
| `src/hooks/`         | Custom React hooks (e.g. WebSocket subscriptions).   |
| `src/lib/`           | API/WebSocket clients and helpers.                   |
| `src/types/`         | Shared TypeScript types.                             |
| `src/config/`        | Frontend configuration.                              |
| `public/icons/`      | Static icons.                                        |
| `public/training/`   | Static training media.                               |

## Environment

Uses `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` (see root `.env.example`).
