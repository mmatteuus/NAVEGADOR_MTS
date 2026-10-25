import assert from 'node:assert/strict';

const KEY = 'browser_mts_automation_enabled';
let value = true, readFails = false, writeFails = false, sessionReadFails = false, sessionClearFails = false, sessionStopFails = false, delayRead = false, rejectDelayedRead = false, releaseRead;
globalThis.chrome = { storage: { local: {
  get: async () => { if (readFails) throw new Error('READ_TRANSIENT'); if (delayRead) await new Promise(resolve => { releaseRead = resolve; }); if (rejectDelayedRead) throw new Error('READ_AFTER_STOP'); return { [KEY]: value }; },
  set: async obj => { if (writeFails) throw new Error('WRITE_TRANSIENT'); value = obj[KEY]; }
}, session: {
  get: async () => { if (sessionReadFails) throw new Error('SESSION_READ_TRANSIENT'); return {}; },
  set: async obj => { if (sessionStopFails && obj.browser_mts_automation_blocked_session === true) throw new Error('SESSION_STOP_TRANSIENT'); if (sessionClearFails && obj.browser_mts_automation_blocked_session === false) throw new Error('SESSION_CLEAR_TRANSIENT'); }
} } };

const state = await import('../src/extension/background/state_storage.js?storage-regression');
readFails = true;
assert.equal(await state.isAutomationEnabled(), false, 'falha de leitura nega admissão');
readFails = false;
assert.equal(await state.isAutomationEnabled(), true, 'leitura posterior verifica e recupera estado ligado');
value = false;
assert.equal(await state.isAutomationEnabled(), false, 'estado persistido desligado continua negado');
value = true;
assert.equal(await state.setAutomationEnabled(true), true);
assert.equal(await state.isAutomationEnabled(), true);
assert.deepEqual(await Promise.all([state.isAutomationEnabled(), state.isAutomationEnabled()]), [true, true]);

writeFails = true;
await assert.rejects(state.setAutomationEnabled(false), /AUTOMATION_STATE_PERSIST_FAILED/);
assert.equal(await state.isAutomationEnabled(), false, 'falha ao desligar bloqueia imediatamente');
writeFails = false;
assert.equal(await state.setAutomationEnabled(true), true, 'habilitação explícita recupera');
assert.equal(await state.isAutomationEnabled(), true);

await state.setAutomationEnabled(false);
assert.equal(await state.isAutomationEnabled(), false);
await state.setAutomationEnabled(true);
const immediateStop = state.setAutomationEnabled(false);
const immediateRead = state.isAutomationEnabled();
await Promise.all([immediateStop, immediateRead]);
assert.equal(value, false, 'stop imediato persiste antes da leitura seguinte');
assert.equal(await state.isAutomationEnabled(), false);
await state.setAutomationEnabled(true);
await Promise.all([state.setAutomationEnabled(true), state.setAutomationEnabled(false)]);
assert.equal(await state.isAutomationEnabled(), false, 'disable posterior vence enable concorrente');
await Promise.all([state.setAutomationEnabled(false), state.setAutomationEnabled(true)]);
assert.equal(await state.isAutomationEnabled(), true, 'enable posterior vence disable concorrente');

sessionReadFails = true;
assert.equal(await state.isAutomationEnabled(), false, 'falha de leitura da trava também nega');
sessionReadFails = false;
await state.setAutomationEnabled(true);
sessionClearFails = true;
await assert.rejects(state.setAutomationEnabled(true), /AUTOMATION_STATE_PERSIST_FAILED/);
sessionClearFails = false;
assert.equal(await state.isAutomationEnabled(), false, 'falha ao limpar trava mantém bloqueio');
await state.setAutomationEnabled(true);
assert.equal(await state.isAutomationEnabled(), true);

delayRead = true;
const pendingRead = state.isAutomationEnabled();
await new Promise(resolve => setTimeout(resolve, 0));
const pendingStop = state.setAutomationEnabled(false);
rejectDelayedRead = true;
releaseRead();
await Promise.allSettled([pendingRead, pendingStop]);
delayRead = false;
rejectDelayedRead = false;
assert.equal(await state.isAutomationEnabled(), false, 'stop vence leitura pendente');
await state.setAutomationEnabled(true);
sessionStopFails = true;
await assert.rejects(state.setAutomationEnabled(false), /AUTOMATION_STATE_PERSIST_FAILED/);
sessionStopFails = false;
assert.equal(value, false, 'stop local persiste mesmo quando session falha');
const stopReload = await import('../src/extension/background/state_storage.js?stop-local-reload');
assert.equal(await stopReload.isAutomationEnabled(), false);
await state.setAutomationEnabled(true);
console.log('PASS: automação fail-closed, persistência e recuperação explícita.');
