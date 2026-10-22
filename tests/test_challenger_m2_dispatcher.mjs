/**
 * @file test_challenger_m2_dispatcher.mjs
 * @description Teste adversarial de concorrência e filas em command_dispatcher.js.
 * Estressa rajadas simultâneas multissessão (Alpha, Beta, Gamma) e isolamento de falhas.
 */
import assert from 'node:assert';

const mockStorage = { browser_mts_automation_enabled: true };
const openTabs = [
  { id: 101, url: 'https://alpha.test', active: false, windowId: 1 },
  { id: 201, url: 'https://beta.test', active: false, windowId: 1 },
  { id: 301, url: 'https://gamma.test', active: false, windowId: 1 }
];
const sentWsMessages = [];
let tabDelayMs = 0;

class MockWebSocket {
  static OPEN = 1;
  constructor(url) {
    this.url = url; this.readyState = MockWebSocket.OPEN;
    setTimeout(() => { if (this.onopen) this.onopen(); }, 5);
  }
  send(data) { sentWsMessages.push(JSON.parse(data)); }
  close() { this.readyState = 3; if (this.onclose) this.onclose(); }
}

globalThis.WebSocket = MockWebSocket;
globalThis.chrome = {
  runtime: { getURL: (p) => `chrome-extension://test/${p}` },
  storage: {
    local: {
      get: async (k) => (typeof k === 'string' ? { [k]: mockStorage[k] } : mockStorage),
      set: async (obj) => Object.assign(mockStorage, obj)
    },
    session: { get: async () => ({ browser_mts_session_tab_grants: [101, 201, 301] }), set: async () => {} }
  },
  tabs: {
    query: async () => openTabs,
    get: async (id) => openTabs.find(t => t.id === Number(id)) || null,
    onRemoved: { addListener: () => {} }, onReplaced: { addListener: () => {} },
    sendMessage: async (tabId, msg) => {
      if (tabDelayMs > 0) await new Promise(r => setTimeout(r, tabDelayMs));
      return { success: true, text: `content_response_for_${tabId}` };
    }
  },
  scripting: { executeScript: async () => [{ result: true }] }
};

const { connectWebSocket } = await import('../src/extension/background/ws_client.js');
const { assignTabToSession } = await import('../src/extension/background/session_registry.js');
const { dispatchIncomingCommand } = await import('../src/extension/background/command_dispatcher.js');

const waitForMessages = async (targetCount, maxTimeout = 2000) => {
  const start = Date.now();
  while (sentWsMessages.length < targetCount && Date.now() - start < maxTimeout) {
    await new Promise(r => setTimeout(r, 10));
  }
};

async function testInterleavedBurst() {
  console.log('[TEST 1] Rajada concorrente intercalada Alpha/Beta/Gamma (60 comandos)...');
  assignTabToSession('session_alpha', 101);
  assignTabToSession('session_beta', 201);
  assignTabToSession('session_gamma', 301);
  sentWsMessages.length = 0; tabDelayMs = 2;
  const agents = [
    { sid: 'session_alpha', tid: 101, name: 'alpha' },
    { sid: 'session_beta', tid: 201, name: 'beta' },
    { sid: 'session_gamma', tid: 301, name: 'gamma' }
  ];

  for (let i = 0; i < 20; i++) {
    for (const ag of agents) {
      dispatchIncomingCommand({
        id: `cmd_${ag.name}_${i}`, sessionId: ag.sid, action: 'browser_get_text',
        payload: { tabId: ag.tid, selector: 'body' }
      });
    }
  }

  await waitForMessages(60);
  assert.strictEqual(sentWsMessages.length, 60, `Esperado 60 msgs, obtido ${sentWsMessages.length}`);
  assert.ok(sentWsMessages.every(m => m.success === true), 'Todos os comandos devem ter success=true');

  for (const ag of agents) {
    const agMsgs = sentWsMessages.filter(m => m.sessionId === ag.sid);
    assert.strictEqual(agMsgs.length, 20);
    for (let i = 0; i < 20; i++) {
      assert.strictEqual(agMsgs[i].id, `cmd_${ag.name}_${i}`, `FIFO violado para ${ag.name} no índice ${i}`);
    }
  }
  console.log('  -> PASS: 60 comandos processados com preservação rigorosa da ordem FIFO.');
}

async function testFailureIsolationAndRecovery() {
  console.log('[TEST 2] Rejeição em Alpha não quebra nem atrasa fila de Beta...');
  sentWsMessages.length = 0; tabDelayMs = 0;
  // Alpha tenta acessar aba 201 de Beta -> TAB_ACCESS_DENIED
  dispatchIncomingCommand({
    id: 'cmd_alpha_fail', sessionId: 'session_alpha', action: 'browser_get_text',
    payload: { tabId: 201, selector: 'body' }
  });
  for (let i = 0; i < 5; i++) {
    dispatchIncomingCommand({
      id: `cmd_beta_${i}`, sessionId: 'session_beta', action: 'browser_get_text',
      payload: { tabId: 201, selector: 'body' }
    });
  }
  dispatchIncomingCommand({
    id: 'cmd_alpha_recovery', sessionId: 'session_alpha', action: 'browser_get_text',
    payload: { tabId: 101, selector: 'body' }
  });

  await waitForMessages(7);
  assert.strictEqual(sentWsMessages.length, 7);
  const failMsg = sentWsMessages.find(m => m.id === 'cmd_alpha_fail');
  assert.ok(failMsg && failMsg.success === false && /TAB_ACCESS_DENIED/.test(failMsg.error));

  for (let i = 0; i < 5; i++) {
    const betaMsg = sentWsMessages.find(m => m.id === `cmd_beta_${i}`);
    assert.ok(betaMsg && betaMsg.success === true);
  }
  const recMsg = sentWsMessages.find(m => m.id === 'cmd_alpha_recovery');
  assert.ok(recMsg && recMsg.success === true);
  console.log('  -> PASS: Erro em Alpha isolado; Beta e recuperação de Alpha operaram normalmente.');
}

async function run() {
  await connectWebSocket();
  await new Promise(r => setTimeout(r, 20));
  await testInterleavedBurst();
  await testFailureIsolationAndRecovery();
  console.log('\n[SUCESSO] Todos os testes de concorrência em command_dispatcher.js passaram!');
  process.exit(0);
}

run().catch(err => {
  console.error('\n[FALHA NO DISPATCHER ADVERSARIAL]', err);
  process.exit(1);
});
