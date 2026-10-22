import assert from 'node:assert/strict';

const local = {};
const listeners = [];
globalThis.chrome = {
  runtime: { getManifest: () => ({ version: '2.3.1' }) },
  storage: {
    local: {
      async get(key) { return { [key]: local[key] }; },
      async set(values) { Object.assign(local, values); }
    },
    session: { async get() { return { browser_mts_session_tab_grants: [4, 9] }; } },
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
let refreshes = 0;
installGrantSync(() => { refreshes += 1; });
listeners[0]({ browser_mts_session_tab_grants: { newValue: [9] } }, 'session');
listeners[0]({ unrelated: { newValue: true } }, 'local');
await new Promise(resolve => setTimeout(resolve, 0));
assert.equal(refreshes, 1);
console.log('PASS: identity is stable, grants are announced, and grant changes refresh hello');
