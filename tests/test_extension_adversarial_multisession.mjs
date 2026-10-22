/**
 * @file test_extension_adversarial_multisession.mjs
 * @description Suíte de testes adversariais para Extensão MV3 com foco em multissessão,
 * isolamento estrito de abas (TAB_ACCESS_DENIED) e filtragem de abas por sessão.
 */
import assert from 'node:assert';

const openTabs = [
  { id: 101, url: 'https://site-alpha.test', title: 'Alpha 1', windowId: 10, active: true },
  { id: 102, url: 'https://doc-alpha.test', title: 'Alpha 2', windowId: 10, active: false },
  { id: 201, url: 'https://site-beta.test', title: 'Beta 1', windowId: 20, active: true },
  { id: 202, url: 'https://doc-beta.test', title: 'Beta 2', windowId: 20, active: false }
];

globalThis.WebSocket = class {
  static OPEN = 1;
  constructor() { this.readyState = 1; setTimeout(() => this.onopen?.(), 2); }
  send() {} close() {}
};

globalThis.chrome = {
  runtime: { getURL: p => `chrome-extension://test/${p}` },
  storage: {
    local: { get: async () => ({ browser_mts_automation_enabled: true }), set: async () => {} },
    session: { get: async () => ({ browser_mts_session_tab_grants: [101, 102, 201, 202] }), set: async () => {} }
  },
  tabs: {
    query: async () => openTabs,
    get: async id => openTabs.find(t => t.id === Number(id)) || null,
    sendMessage: async () => ({ success: true })
  }
};

const { assignTabToSession, clearSessionRegistry, validateTabAccess } = await import('../src/extension/background/session_registry.js');
const { popupGrantState, targetId } = await import('../src/extension/background/tab_access.js');

async function testTabListingIsolation() {
  console.log('[TEST 1] Filtragem estrita de abas em popupGrantState por sessão...');
  clearSessionRegistry();
  assignTabToSession('agent_alpha', 101);
  assignTabToSession('agent_alpha', 102);
  assignTabToSession('agent_beta', 201);
  assignTabToSession('agent_beta', 202);

  const tabsAlpha = await popupGrantState(false, 'agent_alpha');
  assert.strictEqual(tabsAlpha.length, 2, 'Alpha deve ver exatamente 2 abas');
  assert.deepStrictEqual(tabsAlpha.map(t => t.id).sort(), [101, 102]);
  assert.ok(tabsAlpha.every(t => t.allowedForAgent === true));

  const tabsBeta = await popupGrantState(false, 'agent_beta');
  assert.strictEqual(tabsBeta.length, 2, 'Beta deve ver exatamente 2 abas');
  assert.deepStrictEqual(tabsBeta.map(t => t.id).sort(), [201, 202]);

  const tabsGamma = await popupGrantState(false, 'agent_gamma');
  assert.strictEqual(tabsGamma.length, 0, 'Agente sem abas deve ver 0 abas');

  const tabsLegacy = await popupGrantState(false, null);
  assert.strictEqual(tabsLegacy.length, 4, 'Modo legado sem sessão visualiza todas as abas');
  console.log('  -> PASS: Isolamento estrito de listagem de abas validado com sucesso.');
}

async function testTargetIdFallThroughPrevention() {
  console.log('[TEST 2] Prevenção de fall-through de targetId entre sessões...');
  clearSessionRegistry();
  assignTabToSession('agent_alpha', 101);
  assignTabToSession('agent_beta', 201);

  const targetAlpha = await targetId(null, 'agent_alpha');
  assert.strictEqual(targetAlpha, 101);

  await assert.rejects(async () => targetId(null, 'agent_gamma'), /TAB_NOT_ALLOWED/);
  await assert.rejects(async () => targetId(201, 'agent_alpha'), /TAB_ACCESS_DENIED/);
  await assert.rejects(async () => targetId(101, 'agent_beta'), /TAB_ACCESS_DENIED/);
  console.log('  -> PASS: Fall-through e acesso cruzado bloqueados estritamente.');
}

async function testCrossSessionActionRejection() {
  console.log('[TEST 3] Rejeição de ações cruzadas no session_registry...');
  assert.throws(() => validateTabAccess('agent_alpha', 201), /TAB_ACCESS_DENIED/);
  assert.throws(() => validateTabAccess('agent_beta', 101), /TAB_ACCESS_DENIED/);
  assert.throws(() => validateTabAccess(null, 101), /TAB_ACCESS_DENIED/);
  assert.strictEqual(validateTabAccess('agent_alpha', 101), true);
  console.log('  -> PASS: Validação fail-closed de posse de aba confirmada.');
}

async function testConcurrentBurstSegregation() {
  console.log('[TEST 4] Rajada de 20 acessos concorrentes em abas segregadas...');
  const promises = [];
  for (let i = 0; i < 10; i++) {
    promises.push((async () => {
      assert.strictEqual(await targetId(101, 'agent_alpha'), 101);
      assert.strictEqual(await targetId(201, 'agent_beta'), 201);
    })());
  }
  await Promise.all(promises);
  console.log('  -> PASS: 20 requisições simultâneas segregadas sem interferência.');
}

async function runAll() {
  console.log('=== TESTES ADVERSARIAIS MULTISSESSÃO: ISOLAMENTO DE ABAS ===\n');
  await testTabListingIsolation();
  await testTargetIdFallThroughPrevention();
  await testCrossSessionActionRejection();
  await testConcurrentBurstSegregation();
  console.log('\n[SUCESSO] Suíte adversarial multissessão aprovada com louvor!');
  process.exit(0);
}

runAll().catch(err => {
  console.error('\n[FALHA NO TESTE MULTISSESSÃO]', err);
  process.exit(1);
});
