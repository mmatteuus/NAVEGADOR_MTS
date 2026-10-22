/** Regressão: browser_manage_tabs não pode depender de content script. */
import assert from 'node:assert/strict';

let tabs = [{ id: 7, url: 'chrome://extensions', title: 'Extensões', active: true, windowId: 1 }];
let injectionAttempts = 0;
const storage = { browser_mts_automation_enabled: true };
const replies = [];
let sessionGrants = [];

class MockWebSocket {
  static OPEN = 1;
  constructor() { this.readyState = MockWebSocket.OPEN; setTimeout(() => this.onopen?.(), 1); }
  send(raw) { replies.push(JSON.parse(raw)); }
  close() { this.readyState = 3; this.onclose?.(); }
}

globalThis.WebSocket = MockWebSocket;
globalThis.chrome = {
  runtime: { getURL: (path) => `chrome-extension://test/${path}` },
  storage: { local: {
    get: async (key) => typeof key === 'string' ? { [key]: storage[key] } : storage,
    set: async (values) => Object.assign(storage, values)
  }, session: {
    get: async () => ({ browser_mts_session_tab_grants: sessionGrants }),
    set: async (data) => { sessionGrants = data.browser_mts_session_tab_grants || []; }
  } },
  tabs: {
    query: async (query) => tabs.filter((tab) => !query.active || tab.active),
    get: async (id) => tabs.find((tab) => tab.id === id) || null,
    onRemoved: { addListener: () => {} }, onReplaced: { addListener: () => {} },
    create: async (options) => {
      const tab = { id: 8, title: '', windowId: 1, ...options };
      tabs = tabs.map((item) => ({ ...item, active: options.active ? false : item.active }));
      tabs.push(tab);
      return tab;
    },
    update: async (id, values) => {
      tabs = tabs.map((tab) => tab.id === id ? { ...tab, ...values } : tab);
      return tabs.find((tab) => tab.id === id);
    },
    remove: async (id) => { tabs = tabs.filter((tab) => tab.id !== id); },
    sendMessage: async () => { throw new Error('content script unavailable'); }
  },
  scripting: { executeScript: async () => { injectionAttempts++; throw new Error('injection forbidden'); } }
};

const { connectWebSocket } = await import('../src/extension/background/ws_client.js');
const { dispatchIncomingCommand } = await import('../src/extension/background/command_dispatcher.js');

await connectWebSocket();
await new Promise((resolve) => setTimeout(resolve, 10));
replies.length = 0;
dispatchIncomingCommand({ id: 'list_restricted', action: 'browser_manage_tabs', params: { action: 'list' } });
await new Promise((resolve) => setTimeout(resolve, 20));
const listReply = replies.find((message) => message.id === 'list_restricted');
assert.equal(listReply?.success, true);
assert.equal(listReply.payload.result[0].url, 'chrome://extensions');
assert.equal(injectionAttempts, 0);

dispatchIncomingCommand({ id: 'new_http', action: 'browser_manage_tabs',
  params: { action: 'new', url: 'https://example.com', active: true } });
await new Promise((resolve) => setTimeout(resolve, 20));
const newReply = replies.find((message) => message.id === 'new_http');
assert.equal(newReply?.success, true);
assert.ok(tabs.some((tab) => tab.url === 'https://example.com'));
assert.equal(injectionAttempts, 0);
console.log('[PASS] browser_manage_tabs opera em chrome:// sem injeção e cria aba HTTP.');
process.exit(0);
