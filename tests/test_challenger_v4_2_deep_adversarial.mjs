/**
 * @file test_challenger_v4_2_deep_adversarial.mjs
 * @description Testes adversariais avançados de isolamento de abas, bypass de targetId e anti-forja.
 */
import assert from 'node:assert/strict';

const openTabs = [
  { id: 10, url: 'https://user-private.bank', title: 'User Bank', active: true, windowId: 1 },
  { id: 101, url: 'https://site-a.com', title: 'Agent A Tab 1', active: false, windowId: 1 },
  { id: 102, url: 'https://site-a2.com', title: 'Agent A Tab 2', active: false, windowId: 1 },
  { id: 201, url: 'https://site-b.com', title: 'Agent B Tab', active: false, windowId: 1 }
];

globalThis.chrome = {
  runtime: { getURL: p => `chrome-extension://test/${p}` },
  storage: {
    local: { get: async () => ({ browser_mts_automation_enabled: true }), set: async () => {} },
    session: { get: async () => ({ browser_mts_session_tab_grants: [10, 101, 102, 201] }), set: async () => {} }
  },
  tabs: {
    query: async () => openTabs,
    get: async id => openTabs.find(t => t.id === Number(id)) || null,
    sendMessage: async () => ({ success: true })
  }
};

const { assignTabToSession, clearSessionRegistry, validateTabAccess, getTabsForSession } =
  await import('../src/extension/background/session_registry.js');
const { targetId } = await import('../src/extension/background/tab_access.js');
const isolator = await import('../src/extension/background/cookie_isolator.js');

async function testUnassignedTabHijacking() {
  console.log('[ADV 1] Tentativa de sequestro de aba do usuário não vinculada a sessões...');
  clearSessionRegistry();
  assignTabToSession('agent_a', 101);
  assignTabToSession('agent_b', 201);

  // Aba 10 é uma aba do usuário (concedida no popup legado, mas não atribuída a nenhuma sessão de agente)
  assert.throws(
    () => validateTabAccess('agent_b', 10),
    /TAB_ACCESS_DENIED/,
    'Agente B não deve conseguir acessar aba de usuário não vinculada a ele'
  );
  await assert.rejects(
    async () => targetId(10, 'agent_b'),
    /TAB_ACCESS_DENIED/
  );
  console.log('  -> PASS: Abas não atribuídas ao agente são inacessíveis por qualquer agente nomeado.');
}

async function testOmittedTabIdAttacks() {
  console.log('[ADV 2] Tentativas de contorno omitindo tabId (ambiguidade ou agente sem abas)...');
  clearSessionRegistry();
  assignTabToSession('agent_a', 101);
  assignTabToSession('agent_a', 102);
  assignTabToSession('agent_b', 201);

  // Agente C sem abas tenta chamar sem tabId -> não pode pegar aba de ninguém
  await assert.rejects(async () => targetId(null, 'agent_c'), /TAB_NOT_ALLOWED/);
  await assert.rejects(async () => targetId(undefined, 'agent_c'), /TAB_NOT_ALLOWED/);

  // Agente A tem 2 abas e omite tabId -> deve exigir desambiguação
  await assert.rejects(async () => targetId(null, 'agent_a'), /TAB_SELECTION_REQUIRED/);

  // Agente B tem exatamente 1 aba e omite tabId -> recebe exclusivamente sua aba 201
  const bAuto = await targetId(null, 'agent_b');
  assert.strictEqual(bAuto, 201, 'Agente B com 1 aba deve resolver exclusivamente sua aba');
  console.log('  -> PASS: Resolução cega de abas previne cross-talk e exige seleção estrita.');
}

async function testSessionIDCaseAndFormattingTricks() {
  console.log('[ADV 3] Tentativas de forja de sessão via case/whitespace...');
  clearSessionRegistry();
  assignTabToSession('agent_alpha', 101);

  assert.throws(() => validateTabAccess('AGENT_ALPHA', 101), /TAB_ACCESS_DENIED/);
  assert.throws(() => validateTabAccess('agent_alpha ', 101), /TAB_ACCESS_DENIED/);
  assert.throws(() => validateTabAccess(' agent_alpha', 101), /TAB_ACCESS_DENIED/);
  assert.throws(() => validateTabAccess('', 101), /TAB_ACCESS_DENIED/);
  assert.throws(() => validateTabAccess(null, 101), /TAB_ACCESS_DENIED/);
  console.log('  -> PASS: Variações de casing e formatação não conseguem burlar posse.');
}

async function testSubdomainAndOriginStorageIsolation() {
  console.log('[ADV 4] Isolamento de LocalStorage entre subdomínios e origens diferentes...');
  isolator.clearSessionStorage('agent_a');
  isolator.clearSessionStorage('agent_b');

  isolator.setSessionLocalStorage('agent_a', 'https://api.corp.test', 'token', 'TOK_API_A');
  isolator.setSessionLocalStorage('agent_a', 'https://app.corp.test', 'token', 'TOK_APP_A');

  assert.strictEqual(isolator.getSessionLocalStorage('agent_b', 'https://api.corp.test', 'token'), null);
  assert.strictEqual(isolator.getSessionLocalStorage('agent_b', 'https://app.corp.test', 'token'), null);

  assert.strictEqual(isolator.getSessionLocalStorage('agent_a', 'https://api.corp.test', 'token'), 'TOK_API_A');
  assert.strictEqual(isolator.getSessionLocalStorage('agent_a', 'https://app.corp.test', 'token'), 'TOK_APP_A');
  console.log('  -> PASS: Armazenamento segregado por origem e sessão simultaneamente.');
}

async function run() {
  await testUnassignedTabHijacking();
  await testOmittedTabIdAttacks();
  await testSessionIDCaseAndFormattingTricks();
  await testSubdomainAndOriginStorageIsolation();
  console.log('\n[CHALLENGER V4_2 DEEP ADVERSARIAL] Todos os cenários avançados foram aprovados!');
}

run().catch(err => {
  console.error('\n[FALHA FATAL NO TESTE ADVERSARIAL AVANÇADO]', err);
  process.exit(1);
});
