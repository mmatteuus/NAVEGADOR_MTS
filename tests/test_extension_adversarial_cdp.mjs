/**
 * @file test_extension_adversarial_cdp.mjs
 * @description Testes adversariais de resiliência CDP e ciclo de vida do debugger.
 */
import assert from 'node:assert';

const cdpCalls = [];
let onDetachHandler = null;

globalThis.chrome = {
  debugger: {
    attach: async ({ tabId }, version) => {
      cdpCalls.push({ call: 'attach', tabId, version });
      if (tabId === 999 || tabId < 0) throw new Error(`No tab with given id ${tabId}`);
      if (tabId === 888) throw new Error('already attached to tab 888');
    },
    detach: async ({ tabId }) => {
      cdpCalls.push({ call: 'detach', tabId });
      if (tabId === 777) throw new Error('Detach error from browser');
    },
    sendCommand: async ({ tabId }, method, params) => {
      cdpCalls.push({ call: 'sendCommand', tabId, method, params });
      if (method === 'fail') throw new Error('CDP internal Blink error');
      return { result: true };
    },
    onDetach: {
      addListener: (fn) => { onDetachHandler = fn; }
    }
  }
};

const { attachTab, detachTab, sendCdpCommand, isTabAttached, detachAllTabs } =
  await import('../src/extension/background/cdp_controller.js');

async function testAdversarialCdp() {
  console.log('[TEST CDP] 1. Rejeição de parâmetros inválidos em attachTab...');
  for (const badId of [null, undefined, 'abc', 0, NaN, {}]) {
    await assert.rejects(async () => attachTab(badId), /ID de aba inválido/);
  }

  console.log('[TEST CDP] 2. Tratamento de aba inexistente / negativa...');
  await assert.rejects(async () => attachTab(999), /No tab with given id 999/);
  await assert.rejects(async () => attachTab(-1), /No tab with given id -1/);
  assert.strictEqual(isTabAttached(999), false);
  assert.strictEqual(isTabAttached(-1), false);

  console.log('[TEST CDP] 3. Recuperação transparente de already attached...');
  const resAlready = await attachTab(888);
  assert.strictEqual(resAlready, true);
  assert.strictEqual(isTabAttached(888), true);
  await detachTab(888);

  console.log('[TEST CDP] 4. Disparo espontâneo de onDetach e resiliência de entrada...');
  await attachTab(101);
  assert.strictEqual(isTabAttached(101), true);
  assert.doesNotThrow(() => onDetachHandler(null, 'test'));
  assert.doesNotThrow(() => onDetachHandler({}, 'test'));
  assert.doesNotThrow(() => onDetachHandler({ tabId: 9999 }, 'test'));
  assert.strictEqual(isTabAttached(101), true);

  onDetachHandler({ tabId: 101 }, 'target_closed');
  assert.strictEqual(isTabAttached(101), false);

  console.log('[TEST CDP] 5. Reanexação bem-sucedida após onDetach...');
  await sendCdpCommand(101, 'Page.enable');
  assert.strictEqual(isTabAttached(101), true);

  console.log('[TEST CDP] 6. Falha no comando CDP repassa erro sem corromper estado...');
  await assert.rejects(async () => sendCdpCommand(101, 'fail'), /CDP internal Blink error/);

  console.log('[TEST CDP] 7. Desanexação com erro do browser e detachAllTabs em lote...');
  await attachTab(777);
  await attachTab(102);
  const detachRes = await detachTab(777);
  assert.strictEqual(detachRes, false);
  assert.strictEqual(isTabAttached(777), false);

  await detachAllTabs();
  assert.strictEqual(isTabAttached(101), false);
  assert.strictEqual(isTabAttached(102), false);

  console.log('\n[SUCESSO CDP] 100% dos testes adversariais de CDP passaram!');
  process.exit(0);
}

testAdversarialCdp().catch(err => {
  console.error('[FALHA NO TESTE ADVERSARIAL CDP]', err);
  process.exit(1);
});
