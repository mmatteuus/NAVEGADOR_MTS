import assert from 'node:assert/strict';

const local = {};
const listeners = [];
globalThis.chrome = {
  runtime: { getManifest: () => ({ version: '2.3.3' }) },
  storage: {
    local: {
      async get(key) { return { [key]: local[key] }; },
      async set(values) { Object.assign(local, values); }
    },
    session: { async get(key) { return key === 'browser_mts_popup_tab_owners'
      ? { browser_mts_popup_tab_owners: { 4: 'agent-a' } }
      : { browser_mts_session_tab_grants: [4, 9] }; } },
    onChanged: { addListener(fn) { listeners.push(fn); } }
  }
};

const { createClientHello, getClientInstanceId, installGrantSync } =
  await import('../src/extension/background/extension_identity.js');
const ids = await Promise.all([getClientInstanceId(), getClientInstanceId()]);
assert.equal(ids[0], ids[1]);
const hello = await createClientHello({ id: 4 });
assert.equal(hello.payload.instanceId, ids[0]);
assert.deepEqual(hello.payload.grantedTabIds, [4, 9]);
assert.deepEqual(hello.payload.tabAssignments, { 4: 'agent-a' });
let refreshes = 0;
installGrantSync(() => { refreshes += 1; });
listeners[0]({ browser_mts_session_tab_grants: { oldValue: [4, 9], newValue: [9] } }, 'session');
listeners[0]({ browser_mts_popup_tab_owners: { oldValue: { 4: 'agent-a' }, newValue: {} } }, 'session');
listeners[0]({ unrelated: { oldValue: false, newValue: true } }, 'local');
await new Promise(resolve => setTimeout(resolve, 0));
assert.equal(refreshes, 2);
console.log('PASS: identity is stable, grants are announced, and grant changes refresh hello');
