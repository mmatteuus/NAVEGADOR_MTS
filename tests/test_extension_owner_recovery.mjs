import assert from 'node:assert/strict';
let fail = true, store = { browser_mts_session_tab_grants: [31], browser_mts_popup_tab_owners: {} };
globalThis.chrome = {
  runtime: { getURL: p => `chrome-extension://test/${p}` },
  storage: { session: {
    get: async key => { if (fail && key === 'browser_mts_popup_tab_owners') throw new Error('TRANSIENT_READ'); return { [key]: store[key] }; },
    set: async value => { store = { ...store, ...value }; }
  } },
  tabs: { query: async () => [{ id: 31, url: 'https://recover.test' }], onRemoved: { addListener() {} }, onReplaced: { addListener() {} } }
};
const policy = await import('../src/extension/background/tab_access.js?owner-recovery');
await assert.rejects(policy.grantedTabs(), /TRANSIENT_READ/);
fail = false;
assert.deepEqual(await policy.grantedTabs(), [31]);
console.log('PASS: carregamento de owners recupera após falha transitória.');
