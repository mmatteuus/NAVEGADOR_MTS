import assert from 'node:assert/strict';

let tabs = [
  { id: 21, url: 'https://alpha.test', title: 'A', windowId: 1 },
  { id: 22, url: 'https://beta.test', title: 'B', windowId: 1 }
];
let store = { browser_mts_session_tab_grants: [21, 22], browser_mts_popup_tab_owners: {} };
globalThis.chrome = {
  runtime: { getURL: p => `chrome-extension://test/${p}` },
  storage: { session: {
    get: async key => key ? { [key]: store[key] } : store,
    set: async value => { store = { ...store, ...value }; }
  } },
  tabs: {
    query: async () => tabs,
    get: async id => tabs.find(tab => tab.id === Number(id)) || null,
    onRemoved: { addListener() {} }, onReplaced: { addListener() {} }
  }
};
const { setAgentDirectory } = await import('../src/extension/background/agent_directory.js');
const policy = await import('../src/extension/background/tab_access.js');
setAgentDirectory([{ sessionId: 'agent-a', agentId: 'A' }, { sessionId: 'agent-b', agentId: 'B' }]);
const popup = { url: 'chrome-extension://test/popup/popup.html' };
await policy.assignFromPopup({ assignments: [
  { tabId: 21, sessionId: 'agent-a' }, { tabId: 22, sessionId: 'agent-b' }
] }, popup);
assert.equal(await policy.targetId(21, 'agent-a'), 21);
await assert.rejects(policy.targetId(21, 'agent-b'), /TAB_ACCESS_DENIED/);
await policy.assignFromPopup({ assignments: [{ tabId: 21, sessionId: 'agent-b', expectedSessionId: 'agent-a' }] }, popup);
assert.equal(await policy.targetId(21, 'agent-b'), 21);
await assert.rejects(policy.targetId(21, 'agent-a'), /TAB_ACCESS_DENIED/);
await assert.rejects(policy.assignFromPopup({ revocations: [{ tabId: 21, expectedSessionId: 'agent-a' }] }, popup), /AGENT_ASSIGNMENT_STALE/);
await policy.assignFromPopup({ revocations: [{ tabId: 21, expectedSessionId: 'agent-b' }] }, popup);
assert.deepEqual(await policy.grantedTabs(), [22], 'desmarcar remove somente a aba do agente');
await assert.rejects(policy.assignFromPopup({ assignments: [{ tabId: 21, sessionId: 'missing' }] }, popup), /AGENT_NOT_AVAILABLE/);
await policy.assignFromPopup({ assignments: [{ tabId: 21, sessionId: 'agent-a', expectedSessionId: '' }] }, popup);
const originalSet = chrome.storage.session.set;
chrome.storage.session.set = async value => {
  if (Object.prototype.hasOwnProperty.call(value, 'browser_mts_popup_tab_owners')) throw new Error('STORAGE_TRANSIENT');
  return originalSet(value);
};
await assert.rejects(policy.assignFromPopup({ assignments: [{ tabId: 21, sessionId: 'agent-b', expectedSessionId: 'agent-a' }] }, popup), /STORAGE_TRANSIENT/);
chrome.storage.session.set = originalSet;
assert.equal(await policy.targetId(21, 'agent-a'), 21, 'falha de persistência não troca o dono em memória');
tabs.push({ id: 23, url: 'https://new.test', title: 'N' , windowId: 1 });
chrome.storage.session.set = async value => {
  if (Object.prototype.hasOwnProperty.call(value, 'browser_mts_popup_tab_owners')) throw new Error('STORAGE_FIRST_WRITE');
  return originalSet(value);
};
await assert.rejects(policy.assignFromPopup({ assignments: [{ tabId: 23, sessionId: 'agent-a', expectedSessionId: '' }] }, popup), /STORAGE_FIRST_WRITE/);
chrome.storage.session.set = originalSet;
await assert.rejects(policy.targetId(23, 'agent-a'), /TAB_(NOT_ALLOWED|ACCESS_DENIED)/);
console.log('PASS: atribuição explícita, reassociação humana e bloqueio cruzado.');
