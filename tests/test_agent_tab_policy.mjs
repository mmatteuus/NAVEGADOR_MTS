/** QA independente da allowlist de abas do agente.
 * Usa apenas mocks da API Chrome; nenhum navegador real é aberto.
 */
import assert from 'node:assert/strict';

let tabs = [
  { id: 11, windowId: 1, title: 'Primeira', url: 'https://a.test', active: true },
  { id: 12, windowId: 1, title: 'Segunda', url: 'https://b.test', active: false }
];
let grants = [];
const removed = { addListener: () => {} };
const replaced = { addListener: () => {} };

globalThis.chrome = {
  runtime: { getURL: (path) => `chrome-extension://test/${path}` },
  storage: { session: {
    get: async () => ({ browser_mts_session_tab_grants: grants }),
    set: async (value) => { grants = value.browser_mts_session_tab_grants; }
  } },
  tabs: {
    query: async () => tabs,
    get: async (id) => tabs.find((tab) => tab.id === id) || null,
    create: async ({ url, active }) => { const tab = { id: 13, windowId: 1, title: '', url, active }; tabs.push(tab); return tab; },
    onRemoved: removed,
    onReplaced: replaced
  }
};

const policy = await import('../src/extension/background/tab_access.js');
const popup = { url: 'chrome-extension://test/popup/popup.html' };

await assert.rejects(
  policy.grantFromPopup({ tabIds: [11] }, { url: 'https://attacker.test' }),
  /GRANT_FORBIDDEN/
);
assert.deepEqual(grants, []);

await policy.grantFromPopup({ tabIds: [11] }, popup);
assert.equal(await policy.targetId(), 11, 'uma aba permite alvo implícito determinístico');
await assert.rejects(policy.targetId(12), /TAB_NOT_ALLOWED/);

await policy.grantFromPopup({ tabIds: [11, 12] }, popup);
await assert.rejects(policy.targetId(), /TAB_SELECTION_REQUIRED/);
assert.equal(await policy.targetId(12), 12);

tabs = tabs.filter((tab) => tab.id !== 12);
assert.deepEqual(await policy.grantedTabs(), [11], 'aba fechada é removida da sessão');
assert.equal(await policy.targetId(), 11);

await assert.rejects(
  policy.grantFromPopup({ tabIds: [99] }, popup),
  /TAB_NOT_FOUND/
);
assert.deepEqual(grants, [11]);

const opened = await policy.openGrantedTab({ url: 'https://novo.test' }, popup);
assert.equal(opened.find(tab => tab.url === 'https://novo.test')?.allowedForAgent, true);
assert.equal(tabs.at(-1).active, false, 'aba aberta pelo popup não pode roubar foco');
await assert.rejects(
  policy.openGrantedTab({ url: 'https://attacker.test' }, { url: 'https://evil.test' }),
  /GRANT_FORBIDDEN/
);
await assert.rejects(policy.openGrantedTab({ url: 'chrome://settings' }, popup), /URL_NOT_ALLOWED/);
await Promise.all([policy.grantedTabs(), policy.clearGrants()]);
assert.deepEqual(grants, [], 'pruning concorrente não pode ressuscitar grants antigos');
tabs.push({ id: 14, windowId: 1, title: 'Extensão', url: 'chrome-extension://test/popup/popup.html', active: false });
await assert.rejects(policy.grantFromPopup({ tabIds: [14] }, popup), /TAB_NOT_ALLOWED/);
console.log('[PASS] allowlist de uma/múltiplas abas, negação e limpeza validadas.');
