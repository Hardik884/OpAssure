/** Backend URLs. Set via NEXT_PUBLIC_API_URL / NEXT_PUBLIC_WS_URL (repo-root .env, see next.config.ts). */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "";

/**
 * Whether the app runs against mock data or the real backend. Later prompts flip
 * this default (or make it runtime-configurable); for this foundation prompt the
 * whole app reads mock data through the same lib/api.ts + hooks surface it will
 * use for real data, so no components need to change when that flag flips.
 */
export const USE_MOCK_DATA = true;
