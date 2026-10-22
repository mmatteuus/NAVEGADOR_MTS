/** Regressão: concessão do popup deve ser utilizável por uma sessão MCP. */
import assert from 'node:assert/strict';

let tabs = [
  { id: 7, url: 'https://one.test', title: 'Uma', windowId: 1, active: true },
  { id: 8, url: 'https://two.test', title: 'Duas', windowId: 1, active: false }
];
let grants = [7, 8];
let owners = {};
const replacedListeners = [];

globalThis.chrome = {
  runtime: { getURL: path => `chrome-extension://test/${path}` },
  storage: { session: {
    get: async key => key === 'browser_mts_session_tab_grants'
      ? { browser_mts_session_tab_grants: grants }
      : { browser_mts_popup_tab_owners: owners },
    set: async values => {
      if (values.browser_mts_session_tab_grants) grants = values.browser_mts_session_tab_grants;
      if (values.browser_mts_popup_tab_owners) owners = values.browser_mts_popup_tab_owners;
    }
  } },
  tabs: {
    query: async query => tabs.filter(tab => !query?.currentWindow || tab.windowId === 1),
    get: async id => tabs.find(tab => tab.id === Number(id)) || null,
    onRemoved: { addListener() {} }, onReplaced: { addListener: fn => replacedListeners.push(fn) }
  }
};

const { targetId, popupGrantState, clearGrants } = await import('../src/extension/background/tab_access.js');
const { assignTabToSession, clearSessionRegistry, getSessionForTab } = await import('../src/extension/background/session_registry.js');

assert.equal(await targetId(7, 'agent_a'), 7, 'sessão deve reivindicar concessão explícita');
await assert.rejects(() => targetId(7, 'agent_b'), /TAB_ACCESS_DENIED/);
assert.deepEqual((await popupGrantState(false, 'agent_b')).map(tab => tab.id), [8]);
assert.equal(await targetId(undefined, 'agent_b'), 8, 'única concessão livre deve ser selecionável');
clearSessionRegistry();
const restartedAccess = await import('../src/extension/background/tab_access.js?worker_restart');
await assert.rejects(() => restartedAccess.targetId(7, 'agent_b'), /TAB_ACCESS_DENIED/, 'ownership deve sobreviver ao restart');
tabs.push({ id: 17, url: 'https://replacement.test', title: 'Troca', windowId: 1 });
for (const listener of replacedListeners) await listener(17, 7);
assert.equal(getSessionForTab(7), null, 'aba substituída deve perder claim');
assignTabToSession('agent_owned', 17);
await clearGrants();
assert.deepEqual(grants, []);
assert.equal(getSessionForTab(17), 'agent_owned', 'clear do popup não pode liberar aba criada pelo agente');
console.log('PASS: concessões do popup são reivindicadas por sessão e permanecem isoladas.');
process.exit(0);
