/**
 * @file fixture_http_server.mjs
 * @description Servidor HTTP local efêmero para teste empírico de isolamento
 * de cookies (Set-Cookie) e localStorage entre múltiplos contextos de agentes.
 */
import { createServer } from 'node:http';

export function createTestHttpServer() {
  const stats = { requestsA: 0, requestsB: 0, cookiesReceivedInB: [] };

  const server = createServer((req, res) => {
    const url = new URL(req.url, `http://${req.headers.host || '127.0.0.1'}`);

    if (url.pathname === '/agent-a/set-auth') {
      stats.requestsA++;
      res.writeHead(200, {
        'Content-Type': 'text/html; charset=utf-8',
        'Set-Cookie': 'session_token=ALPHA_SECRET_TOKEN_777; Path=/; SameSite=Lax'
      });
      res.end(`<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Agent A Auth</title></head>
<body>
  <div id="auth-status">AUTH_CONFIGURED_FOR_AGENT_A</div>
  <script>
    localStorage.setItem('agent_storage_key', 'ALPHA_STORAGE_SECRET_888');
  </script>
</body>
</html>`);
      return;
    }

    if (url.pathname === '/agent-b/check-auth') {
      stats.requestsB++;
      const cookieHeader = req.headers.cookie || '';
      const hasToken = cookieHeader.includes('ALPHA_SECRET_TOKEN_777');
      if (hasToken) {
        stats.cookiesReceivedInB.push(cookieHeader);
      }
      const cookieStatus = hasToken ? 'LEAKED' : 'CLEAN';

      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(`<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Agent B Check</title></head>
<body>
  <div id="cookie-leak">${cookieStatus}</div>
  <div id="storage-leak">PENDING</div>
  <script>
    const val = localStorage.getItem('agent_storage_key');
    document.getElementById('storage-leak').textContent = val ? 'LEAKED' : 'CLEAN';
  </script>
</body>
</html>`);
      return;
    }

    if (url.pathname === '/stats') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(stats));
      return;
    }

    if (url.pathname === '/stop' && req.method === 'POST') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ stopped: true }));
      setImmediate(() => server.close());
      return;
    }

    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not Found');
  });

  return {
    stats,
    start: () => new Promise((resolve, reject) => {
      server.listen(0, '127.0.0.1', () => {
        const port = server.address().port;
        resolve({
          server,
          port,
          url: `http://127.0.0.1:${port}`,
          stats,
          stop: () => new Promise(resStop => server.close(resStop))
        });
      });
      server.once('error', reject);
    })
  };
}
