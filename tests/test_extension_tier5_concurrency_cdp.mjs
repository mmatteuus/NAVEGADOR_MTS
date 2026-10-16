/**
 * @file test_extension_tier5_concurrency_cdp.mjs
 * @description Auditoria adversarial Tier 5: Concorrência CDP, rajada de screenshots e ciclo de vida.
 */
import assert from 'node:assert';

const attachedSet = new Set();
const debuggerCalls = [];
let onDetachCallback = null;

globalThis.chrome = {
  debugger: {
    attach: async ({ tabId }, version) => {
      debuggerCalls.push({ action: 'attach', tabId, version });
      if (attachedSet.has(tabId)) throw new Error(`already attached to tab ${tabId}`);
      attachedSet.add(tabId);
    },
    detach: async ({ tabId }) => {
      debuggerCalls.push({ action: 'detach', tabId });
      attachedSet.delete(tabId);
    },
    sendCommand: async ({ tabId }, method, params) => {
      debuggerCalls.push({ action: 'sendCommand', tabId, method });
      if (!attachedSet.has(tabId)) throw new Error(`Not attached to tab ${tabId}`);
      if (method === 'Page.captureScreenshot') {
        return { data: `BASE64_CDP_TAB_${tabId}` };
      }
      return { success: true };
    },
    onDetach: {
      addListener: (fn) => { onDetachCallback = fn; }
    }
  },
  tabs: {
    get: async (id) => ({ id, url: `https://test-tab-${id}.com`, windowId: 10 }),
    query: async () => [{ id: 1001, url: 'https://test-tab-1001.com', windowId: 10 }]
  }
};

const { attachTab, detachTab, sendCdpCommand, isTabAttached, detachAllTabs } =
  await import('../src/extension/background/cdp_controller.js');
const { cdpCaptureScreenshot, cdpDispatchMouse, cdpDispatchKey, cdpDispatchDrag } =
  await import('../src/extension/background/cdp_actions.js');
const { captureTabScreenshot } =
  await import('../src/extension/background/screenshot_capture.js');

async function runTier5CdpStress() {
  console.log('[TIER 5 CDP] 1. Rajada massiva simultânea: 50 screenshots concorrentes...');
  const promises = [];
  for (let i = 0; i < 50; i++) {
    const tabId = 1001 + (i % 10); // 10 abas de background distintas
    promises.push(captureTabScreenshot('png', 90, tabId));
  }
  const results = await Promise.all(promises);
  assert.strictEqual(results.length, 50, 'Todas as 50 capturas devem completar.');
  for (const res of results) {
    assert.strictEqual(res.success, true);
    assert.ok(res.base64.startsWith('BASE64_CDP_TAB_'));
  }
  console.log('  -> PASS: 50 capturas simultâneas concluídas sem corrida ou corrupção.');

  console.log('[TIER 5 CDP] 2. Despacho composto concorrente de Mouse, Teclado e Drag via CDP...');
  const actionPromises = [
    cdpDispatchMouse(1001, { type: 'mousePressed', x: 100, y: 150 }),
    cdpDispatchMouse(1002, { type: 'mouseMoved', x: 200, y: 250 }),
    cdpDispatchKey(1003, { type: 'keyDown', text: 'MTS' }),
    cdpDispatchDrag(1004, { startX: 10, startY: 10, endX: 80, endY: 80, steps: 3 }),
    cdpCaptureScreenshot(1005, 'jpeg', 80)
  ];
  const actionRes = await Promise.all(actionPromises);
  assert.strictEqual(actionRes.length, 5);
  for (const r of actionRes) assert.strictEqual(r.success, true);
  console.log('  -> PASS: Operações mistas simultâneas em abas de background OK.');

  console.log('[TIER 5 CDP] 3. Prevenção de vazamento de debugger após fechamento de abas...');
  assert.strictEqual(isTabAttached(1001), true);
  // Simula evento onDetach de 5 abas fechadas abruptamente pelo navegador
  for (let id = 1001; id <= 1005; id++) {
    onDetachCallback({ tabId: id }, 'target_closed');
    assert.strictEqual(isTabAttached(id), false, `Aba ${id} deve estar desanexada.`);
  }

  console.log('[TIER 5 CDP] 4. Limpeza total de conexões e detachAllTabs idempotente...');
  await detachAllTabs();
  for (let id = 1001; id <= 1010; id++) {
    assert.strictEqual(isTabAttached(id), false, `Aba ${id} não pode ter debugger pendente.`);
  }
  // Idempotência: segundo detachAllTabs não lança erro
  await assert.doesNotReject(async () => detachAllTabs());
  console.log('  -> PASS: Ciclo de vida estritamente limpo e sem vazamentos de memória.');

  console.log('\n[SUCESSO TIER 5] Testes de Concorrência e Estresse CDP aprovados com louvor!');
  process.exit(0);
}

runTier5CdpStress().catch((err) => {
  console.error('[FALHA TIER 5 CDP]', err);
  process.exit(1);
});
