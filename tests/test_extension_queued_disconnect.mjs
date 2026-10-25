/** Comandos aguardando fila nao sobrevivem a conexao que os originou. */
import assert from 'node:assert/strict';
const stored = { browser_mts_automation_enabled: true };
const sockets = [], effects = [];
let releaseFirst;
class Socket {
  static OPEN = 1; static CONNECTING = 0; static CLOSING = 2; static CLOSED = 3;
  constructor() {
    this.readyState = 1; this.sent = []; sockets.push(this);
    queueMicrotask(() => this.onopen?.());
  }
  send(data) { this.sent.push(JSON.parse(data)); }
  close() { this.readyState = 3; this.onclose?.(); }
}
globalThis.WebSocket = Socket;
globalThis.chrome = {
  runtime: { getURL: p => `chrome-extension://qa/${p}`, getManifest: () => ({ version: '2.3.3' }) },
  storage: {
    local: { get: async key => ({ [key]: stored[key] }), set: async value => Object.assign(stored, value) },
    session: { get: async () => ({ browser_mts_session_tab_grants: [101] }), set: async () => {} }
  },
  tabs: {
    query: async () => [{ id: 101, url: 'https://qa.test', active: false }],
    get: async id => ({ id, url: 'https://qa.test' }),
    onRemoved: { addListener() {} }, onReplaced: { addListener() {} },
    sendMessage: async (_id, message) => {
      effects.push(message.params.selector);
      if (message.params.selector === 'running') await new Promise(resolve => { releaseFirst = resolve; });
      return { success: true, text: 'ok' };
    }
  }
};
const ws = await import('../src/extension/background/ws_client.js');
const { assignTabToSession } = await import('../src/extension/background/session_registry.js');
const { dispatchIncomingCommand } = await import('../src/extension/background/command_dispatcher.js');
const { getActiveQueueCount } = await import('../src/extension/background/session_queues.js');
const until = async predicate => {
  for (let i = 0; i < 100; i++) {
    if (predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 5));
  }
  throw new Error('timeout da fixture');
};
const dispatch = name => dispatchIncomingCommand({ id: name, sessionId: 'agent',
  action: 'browser_get_text', payload: { tabId: 101, selector: name } });
async function run() {
  await ws.connectWebSocket(); await until(() => sockets.length === 1);
  assignTabToSession('agent', 101);
  dispatch('running'); await until(() => !!releaseFirst);
  dispatch('queued');
  sockets[0].close(); await ws.connectWebSocket(); await until(() => sockets.length === 2);
  releaseFirst(); await until(() => getActiveQueueCount() === 0);
  assert.deepEqual(effects, ['running'], 'conexao encerrada cancela trabalho ainda na fila');
  dispatch('fresh'); await until(() => getActiveQueueCount() === 0);
  assert.deepEqual(effects, ['running', 'fresh']);
  assert.ok(sockets[1].sent.every(item => !['running', 'queued'].includes(item.id)));
  console.log('PASS: fila descarta conexao encerrada sem replay e aceita nova conexao.');
}
run().then(() => process.exit(0), error => { console.error(error); process.exit(1); });
