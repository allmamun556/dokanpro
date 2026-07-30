const CACHE_NAME = "bavaria-genuss-v1";
const STATIC_ASSETS = [
  "/site/index.html",
  "/site/menu.html",
  "/site/css/site.css",
  "/site/js/site-api.js",
  "/site/js/menu.js",
  "/site/icons/icon-192.svg",
  "/site/icons/icon-512.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) =>
        // Precache the menu API response directly at install time too — a page
        // isn't "controlled" by this worker on its very first load, so relying
        // on runtime fetch interception alone would miss that first request.
        cache.addAll(STATIC_ASSETS).then(() => cache.add("/api/public/menu"))
      )
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;

  // Page navigations (including hard reloads): network-first so visitors get
  // the latest page when online, falling back to the cached page when offline.
  if (event.request.mode === "navigate" && url.pathname.startsWith("/site/")) {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return res;
        })
        .catch(() => caches.match(event.request).then((cached) => cached || caches.match("/site/index.html")))
    );
    return;
  }

  // Menu API: network-first so it's fresh when online, falls back to the
  // last-seen response when offline / on flaky restaurant wifi.
  if (url.pathname === "/api/public/menu") {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return res;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Static site assets: cache-first for speed, network fallback if not cached yet.
  if (url.pathname.startsWith("/site/css/") || url.pathname.startsWith("/site/js/") || url.pathname.startsWith("/site/icons/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
  }
});
