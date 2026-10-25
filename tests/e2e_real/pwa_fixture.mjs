/** PWA descartável com Service Worker para QA offline real. */
import { createServer } from 'node:http';

const HTML = `<!doctype html><meta name="viewport" content="width=device-width"><link rel="manifest" href="/manifest.json"><title>PWA QA</title><input id="user" value="preservar"><input id="agent"><script>navigator.serviceWorker.register('/sw.js');</script>`;
const SW = `const CACHE='pwa-qa-v1';self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/','/manifest.json']))));self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||(e.request.mode==='navigate'?caches.match('/') : fetch(e.request)))));`;
const MANIFEST = JSON.stringify({ name: 'PWA QA', short_name: 'PWA QA', start_url: '/', display: 'standalone' });

export function createPwaFixture() {
  const server = createServer((req, res) => {
    const body = req.url === '/sw.js' ? SW : req.url === '/manifest.json' ? MANIFEST : HTML;
    const type = req.url === '/sw.js' ? 'text/javascript' : req.url === '/manifest.json' ? 'application/manifest+json' : 'text/html';
    res.writeHead(200, { 'content-type': type, ...(req.url === '/' ? { 'cache-control': 'no-store' } : {}) });
    res.end(body);
  });
  return {
    async start() {
      await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
      return { url: `http://127.0.0.1:${server.address().port}/` };
    },
    async stop() { await new Promise(resolve => server.close(() => resolve())); }
  };
}
