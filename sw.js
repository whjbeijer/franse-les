// Service worker: haalt alles eerst van internet (zodat je altijd de nieuwste
// versie hebt) en valt terug op de opgeslagen kopie als je offline bent.
const CACHE = 'frans-v2';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        if (res.ok) {
          const kopie = res.clone();
          // Zonder ?t=... opslaan, zodat de woordenlijsten ook offline te vinden zijn
          const sleutel = e.request.url.replace(/[?&]t=\d+/, '');
          caches.open(CACHE).then(c => c.put(sleutel, kopie));
        }
        return res;
      })
      .catch(() => caches.match(e.request.url.replace(/[?&]t=\d+/, '')))
  );
});
