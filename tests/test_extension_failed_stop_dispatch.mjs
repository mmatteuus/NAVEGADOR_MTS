import assert from 'node:assert/strict';
let automation = true, writeFails = false, effects = 0, sessionBlocked = false;
const grants = [1];
globalThis.WebSocket = { OPEN: 1 };
globalThis.chrome = {
  runtime: { getURL: p => `chrome-extension://test/${p}` },
  storage: { local: {
    get: async key => ({ [key]: automation }),
    set: async value => { if (writeFails) throw new Error('WRITE_TRANSIENT'); automation = value.browser_mts_automation_enabled; }
  }, session: {
    get: async key => ({ [key]: key === 'browser_mts_session_tab_grants' ? grants : sessionBlocked }),
    set: async value => { sessionBlocked = value.browser_mts_automation_blocked_session === true; }
  } },
  tabs: {
    query: async () => [{ id: 1, url: 'https://dispatch.test', active: true, windowId: 1 }],
    get: async id => id === 1 ? { id, url: 'https://dispatch.test' } : null,
    sendMessage: async () => { effects += 1; return { success: true, text: 'ok' }; },
    onRemoved: { addListener() {} }, onReplaced: { addListener() {} }
  },
  scripting: { executeScript: async () => [{ result: true }] }
};
const state = await import('../src/extension/background/state_storage.js');
await state.isAutomationEnabled();
const { dispatchIncomingCommand } = await import('../src/extension/background/command_dispatcher.js?failed-stop-dispatch');
const { getActiveQueueCount } = await import('../src/extension/background/session_queues.js');
const waitFor = async predicate => { for (let i = 0; i < 100; i += 1) { if (predicate()) return; await new Promise(resolve => setTimeout(resolve, 5)); } };
dispatchIncomingCommand({ id: 'allowed', action: 'browser_get_text', sessionId: 'agent', params: { tabId: 1, selector: 'body' } });
await waitFor(() => effects === 1 && getActiveQueueCount() === 0);
assert.equal(effects, 1, 'controle positivo executa com concessão e automação ligada');
writeFails = true;
await assert.rejects(state.setAutomationEnabled(false), /AUTOMATION_STATE_PERSIST_FAILED/);
const reloaded = await import('../src/extension/background/state_storage.js?failed-stop-reload');
assert.equal(await reloaded.isAutomationEnabled(), false, 'trava de sessão sobrevive à recarga do worker');
dispatchIncomingCommand({ id: 'blocked', action: 'browser_get_text', sessionId: 'agent', params: { tabId: 1, selector: 'body' } });
await waitFor(() => getActiveQueueCount() === 0);
assert.equal(effects, 1, 'falha ao persistir stop não pode executar nova ação');
console.log('PASS: dispatch permanece fail-closed após stop persistência falhar.');
