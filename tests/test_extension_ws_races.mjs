import assert from 'node:assert/strict';

const stored = { browser_mts_automation_enabled: true, browser_mts_active_port: 3456 };
const sockets = [];
let rejectTabs = true;
let unhandled = 0;
process.on('unhandledRejection', () => { unhandled += 1; });

class MockWebSocket {
  static OPEN = 1; static CONNECTING = 0; static CLOSING = 2; static CLOSED = 3;
  constructor(url) {
    this.url = url; this.readyState = MockWebSocket.CONNECTING; sockets.push(this);
    queueMicrotask(() => { this.readyState = MockWebSocket.OPEN; this.onopen?.(); });
  }
  send(data) { this.sent = this.sent || []; this.sent.push(JSON.parse(data)); }
  close() { this.readyState = MockWebSocket.CLOSED; this.onclose?.(); }
}

globalThis.WebSocket = MockWebSocket;
globalThis.chrome = {
  storage: { local: {
    async get(key) { return { [key]: stored[key] }; },
    async set(values) { Object.assign(stored, values); }
  } },
  tabs: { async query() {
    if (rejectTabs) { rejectTabs = false; throw new Error('tabs temporarily unavailable'); }
    return [{ id: 4, url: 'https://example.test', title: 'Test' }];
  } },
  runtime: { reload() {}, getManifest: () => ({ version: '2.3.3' }) }
};

const { connectWebSocket, sendMessage, getConnectionToken } = await import('../src/extension/background/ws_client.js?race=1');
let dispatched = 0;
const { setCommandDispatcher } = await import('../src/extension/background/ws_client.js?race=1');
setCommandDispatcher(() => { dispatched += 1; });
await connectWebSocket();
await new Promise(resolve => setTimeout(resolve, 20));
assert.equal(unhandled, 0, 'falha assíncrona no handshake não pode escapar como rejeição global');
await new Promise(resolve => setTimeout(resolve, 300));
assert.ok(sockets.length >= 2, 'falha no handshake deve permitir reconexão');

const old = sockets[0];
const oldHandler = old.onmessage;
old.readyState = MockWebSocket.CLOSED;
old.onclose?.();
await new Promise(resolve => setTimeout(resolve, 550));
const current = sockets.at(-1);
assert.notEqual(current, old, 'reconexão deve trocar o socket ativo');
current.sent = [];
sendMessage({ id: 'old-response' }, old);
assert.equal((current.sent || []).length, 0, 'resposta de comando antigo não pode usar socket novo');
sendMessage({ id: 'fresh-response' }, getConnectionToken());
assert.equal((current.sent || []).length, 1, 'resposta do socket atual deve ser enviada');
oldHandler?.({ data: JSON.stringify({ id: 'stale', action: 'browser_click' }) });
assert.equal(dispatched, 0, 'resposta do socket antigo não pode chegar ao socket novo');
current.onmessage?.({ data: JSON.stringify({ id: 'fresh', action: 'browser_click' }) });
assert.equal(dispatched, 1, 'mensagem do socket atual deve continuar sendo entregue');
console.log('PASS: handshake assíncrono e mensagens de socket antigo são isolados.');
process.exit(0);
