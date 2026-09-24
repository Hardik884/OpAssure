/**
 * Minimal app-shell service worker — no PWA framework, just enough for an
 * honest offline demo state. Network-first for everything it intercepts
 * (navigations and static assets alike), falling back to the last cached
 * response only when the network is genuinely unreachable — never
 * cache-first, since Next dev's chunk filenames aren't content-hashed and a
 * cache-first static-asset strategy would serve stale JS forever.
 *
 * This never invents live telemetry: it only ever serves a previously-seen
 * HTML shell, never a synthesized "live" response.
 */
const CACHE_NAME = "opassure-shell-v2";
const SHELL_ROUTES = ["/mission", "/task", "/safety", "/training", "/insights", "/history"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ROUTES).catch(() => undefined)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // never intercept the API/WS origin

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached ?? caches.match("/mission"))),
    );
    return;
  }

  if (url.pathname.startsWith("/_next/static") || url.pathname.startsWith("/icons/")) {
    // Network-first, not cache-first: in dev, Next's chunk filenames aren't
    // content-hashed, so the same URL's bytes change on every edit — a
    // cache-first strategy here would serve stale JS forever. Always try
    // the network; only fall back to cache when genuinely offline.
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request)),
    );
  }
});
