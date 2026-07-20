const CACHE = 'retracker-v7';
const ASSETS = ['./index.html', './manifest.json', './icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))));
});

self.addEventListener('fetch', e => {
  const u = e.request.url;
  if (u.includes('latest.json')) {
    e.respondWith(fetch(e.request).then(r => {
      const rc = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, rc));
      return r;
    }).catch(() => caches.match(e.request)));
  } else {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});
