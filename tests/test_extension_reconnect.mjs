import assert from 'node:assert/strict';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const stored = { browser_mts_active_port: 3456, browser_mts_automation_enabled: true };
const sockets = [];
let available = true;

class MockWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;
  constructor(url) {
    this.url = url; this.readyState = MockWebSocket.CONNECTING; sockets.push(this);
    if (available) setTimeout(() => { this.readyState = MockWebSocket.OPEN; this.onopen?.(); }, 5);
  }
  send() {}
  close() { this.readyState = MockWebSocket.CLOSED; this.onclose?.(); }
}

global.WebSocket = MockWebSocket;
global.chrome = {
  storage: { local: {
    async get(key) { return { [key]: stored[key] }; },
    async set(values) { Object.assign(stored, values); }
  } },
  tabs: { async query() { return [{ id: 1, url: 'https://example.test', title: 'Test' }]; } },
  runtime: { reload() {} }
};

const { connectWebSocket } = await import('../src/extension/background/ws_client.js');
const { createPortRecovery } = await import('../src/extension/background/port_recovery.js');
const fallback = createPortRecovery();
await fallback.load();
const visited = new Set([fallback.currentPort()]);
for (let attempt = 0; attempt < 60; attempt++) {
  fallback.advance();
  visited.add(fallback.currentPort());
}
assert.deepEqual([...visited].sort((a, b) => a - b),
  [3456, 3457, 3458, 3459, 3460, 3461, 3462, 3463, 3464, 3465]);

await connectWebSocket();
await wait(20);
assert.equal(sockets[0].url, 'ws://127.0.0.1:3456');

available = false;
sockets[0].readyState = MockWebSocket.CLOSED;
sockets[0].onclose();
await wait(2500);
available = true;
await wait(700);
assert.ok(sockets.some((candidate) => candidate !== sockets[0]
  && candidate.url === 'ws://127.0.0.1:3456'
  && candidate.readyState === MockWebSocket.OPEN));
assert.equal(stored.browser_mts_active_port, 3456);
console.log('PASS: reconnects through the persisted primary port after a delayed restart');
process.exit(0);
