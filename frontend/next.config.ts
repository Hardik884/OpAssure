import fs from "node:fs";
import path from "node:path";
import type { NextConfig } from "next";

// The project keeps one `.env` at the repo root (see ../.env.example). Next.js only
// reads frontend/.env*, so fall back to the root file for the two public URLs.
function fromRootEnv(key: string): string | undefined {
  if (process.env[key]) return process.env[key];
  const file = path.resolve(process.cwd(), "..", ".env");
  if (!fs.existsSync(file)) return undefined;
  const line = fs.readFileSync(file, "utf8").split(/\r?\n/).find((l) => l.startsWith(`${key}=`));
  return line?.slice(key.length + 1).trim() || undefined;
}

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: fromRootEnv("NEXT_PUBLIC_API_URL") ?? "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: fromRootEnv("NEXT_PUBLIC_WS_URL") ?? "ws://localhost:8000/ws",
  },
};

export default nextConfig;
