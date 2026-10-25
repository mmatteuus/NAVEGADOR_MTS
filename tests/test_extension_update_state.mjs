import assert from 'node:assert/strict';

const state = new Map();
let reloads = 0;
globalThis.chrome = {
  storage: { local: {
    get: async key => ({ [key]: state.get(key) }),
    set: async values => Object.entries(values).forEach(([key, value]) => state.set(key, value))
  } },
  runtime: { reload: () => { reloads += 1; }, getManifest: () => ({ version: '2.2.0' }) }
};

const update = await import('../src/extension/background/ws_update.js?test=1');
const { UPDATE_STATE_KEY, handleExtensionUpdate, confirmExtensionVersion,
  getExtensionUpdateState, notifyUpdateQueueIdle, setUpdateIdleCheck } = update;

setUpdateIdleCheck(() => true);
let result = await handleExtensionUpdate({ desktopVersion: '2.3.3', extensionVersion: '2.2.0', reloadRequired: true });
assert.equal(result.action, 'reload_requested');
assert.equal(reloads, 1);
assert.equal((await getExtensionUpdateState()).status, 'reloading');

result = await handleExtensionUpdate({ desktopVersion: '2.3.3', extensionVersion: '2.2.0', reloadRequired: true });
assert.equal(result.action, 'already_requested');
assert.equal(reloads, 1, 'a mesma versão alvo não pode entrar em loop de reload');

await confirmExtensionVersion('2.2.0');
assert.equal((await getExtensionUpdateState()).status, 'error', 'versão antiga após reload precisa virar erro');
await handleExtensionUpdate({ desktopVersion: '2.3.3', reloadRequired: true });
assert.equal(reloads, 1, 'erro após reload não pode reiniciar o ciclo na reconexão seguinte');
await confirmExtensionVersion('2.3.3');
assert.equal((await getExtensionUpdateState()).status, 'confirmed');

setUpdateIdleCheck(() => false);
let settled = false;
const updatePayload = { desktopVersion: '2.4.0', extensionVersion: '2.3.3', reloadRequired: true };
const deferred = handleExtensionUpdate(updatePayload).then(value => { settled = true; return value; });
const duplicate = handleExtensionUpdate(updatePayload);
await new Promise(resolve => setTimeout(resolve, 10));
assert.equal(settled, false, 'reload deve aguardar as filas de comandos');
assert.equal(reloads, 1);
setUpdateIdleCheck(() => true); notifyUpdateQueueIdle();
result = await deferred;
assert.equal(result.action, 'reload_requested');
assert.equal((await duplicate).action, 'already_requested');
assert.equal(reloads, 2);

await confirmExtensionVersion('2.3.3');
const failed = await getExtensionUpdateState();
assert.equal(failed.status, 'error');
assert.match(failed.error, /continua com a versão antiga/);
assert.ok(state.has(UPDATE_STATE_KEY));
state.clear();
result = await handleExtensionUpdate({ desktopVersion: '2.5.0', extensionVersion: '9.0.0',
  extensionUpdateRequired: false, reloadRequired: false });
assert.equal(result.action, 'diagnostic', 'flags da ponte não substituem a versão real do manifesto');
assert.equal(result.actualVersion, '2.2.0');
const originalSet = chrome.storage.local.set;
let writes = 0;
chrome.storage.local.set = async values => {
  if (++writes === 2) throw new Error('storage indisponível na etapa reloading');
  return originalSet(values);
};
state.clear();
result = await handleExtensionUpdate({ desktopVersion: '2.6.0', reloadRequired: true });
assert.equal(result.action, 'error');
assert.equal(reloads, 2, 'falha na segunda gravação não pode iniciar reload');
assert.equal(update.isUpdateAdmissionBlocked(), false);
chrome.storage.local.set = originalSet;
console.log('PASS: update state persists, reload is deferred, deduplicated and confirmed diagnostically.');
