"use client";

/** Real browser connectivity — never a stand-in for the WebSocket's live/demo mode. */
import { useEffect, useState } from "react";

function readInitialOnline(): boolean {
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

export function useOnlineStatus(): boolean {
  // Lazy initializer reads the real value on first client render — no setState-in-effect needed.
  const [online, setOnline] = useState(readInitialOnline);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return online;
}
