// ── Service Worker ────────────────────────────────────────────────────────────
// Network-first strategy: always try the network (bypassing Safari's disk
// cache) and fall back to the cached copy only when offline.
// To force all clients to pick up a new SW version, increment CACHE_NAME.

const CACHE_NAME = 'portfolio-v1';

self.addEventListener('fetch', event => {
    const req = event.request;

    // Only handle GET requests from our own origin.
    // Cross-origin requests (GitHub API, fonts, etc.) are left alone.
    if (req.method !== 'GET' || !req.url.startsWith(self.location.origin)) return;

    event.respondWith(
        // cache: 'no-cache' tells the browser to validate with the server on
        // every request rather than serving directly from its disk cache.
        // This is the key that prevents Safari from showing stale content.
        fetch(req, { cache: 'no-cache' })
            .then(response => {
                // Store a fresh copy so we can serve it offline later.
                const copy = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
                return response;
            })
            .catch(() => caches.match(req))
    );
});

self.addEventListener('activate', event => {
    // Delete caches left behind by any previous SW version.
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});
