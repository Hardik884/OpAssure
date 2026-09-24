/** Backend URLs. Set via NEXT_PUBLIC_API_URL / NEXT_PUBLIC_WS_URL (repo-root .env, see next.config.ts). */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "";

/**
 * Whether the app runs against mock data or the real backend. Defaults to
 * real data (`lib/api.ts` now maps every function to an actual backend
 * endpoint — see docs/api/README.md). Set `NEXT_PUBLIC_USE_MOCK_DATA=true`
 * to work on the UI without a running backend/database; every screen reads
 * through the same lib/api.ts + hooks surface either way, so no component
 * changes are needed when this flips. Falls back to mock automatically if
 * `NEXT_PUBLIC_API_URL` isn't set at all, so a fresh `npm run dev` with no
 * `.env` still renders something instead of an error screen.
 */
export const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true" || !API_URL;
