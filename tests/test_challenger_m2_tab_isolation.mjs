/**
 * @file test_challenger_m2_tab_isolation.mjs
 * @description Testes empíricos adversariais de isolamento de abas (Challenger 2).
 * Valida que Agente B e anônimos são estritamente bloqueados com TAB_ACCESS_DENIED.
 */
import assert from 'node:assert/strict';

let tabs = [
  { id: 101, windowId: 1, title: 'Alpha Private', url: 'https://alpha.internal', active: true },
  { id: 201, windowId: 2, title: 'Beta Workspace', url: 'https://beta.internal', active: false }
];
let grants = [];
globalThis.chrome = {
  runtime: { getURL: (p) => `chrome-extension://test/${p}` },
  storage: { session: {
    get: async () => ({ browser_mts_session_tab_grants: grants }),
    set: async (v) => { grants = v.browser_mts_session_tab_grants; }
  } },
  tabs: {
    query: async () => tabs,
    get: async (id) => tabs.find(t => t.id === id) || null,
    onRemoved: { addListener: () => {} },
    onReplaced: { addListener: () => {} }
  },
  windows: { onRemoved: { addListener: () => {} } }
};

const registry = await import('../src/extension/background/session_registry.js');
const access = await import('../src/extension/background/tab_access.js');

registry.clearSessionRegistry();
registry.assignTabToSession('agent_alpha', 101);
registry.assignTabToSession('agent_beta', 201);

const ACTIONS = ['browser_click', 'browser_type', 'browser_navigate', 'browser_close_tab', 'browser_screenshot'];

console.log('[CHALLENGER 2] Testando tentativas do Agente B invadir aba do Agente A...');
for (const act of ACTIONS) {
  // 1. Invasão direta com tabId de Alpha especificado
  assert.throws(
    () => registry.validateTabAccess('agent_beta', 101),
    /TAB_ACCESS_DENIED: A aba solicitada pertence a outra sessão de agente\./,
    `Agente B não pode validar acesso para aba de Alpha na ação ${act}`
  );
  await assert.rejects(
    access.targetId(101, 'agent_beta'),
    /TAB_ACCESS_DENIED: A aba solicitada pertence a outra sessão de agente\./,
    `targetId deve rejeitar Agente B na aba de Alpha para ação ${act}`
  );
  await assert.rejects(
    access.requireGranted(101, 'agent_beta'),
    /TAB_ACCESS_DENIED: A aba solicitada pertence a outra sessão de agente\./,
    `requireGranted deve rejeitar Agente B na aba de Alpha para ação ${act}`
  );
}

console.log('[CHALLENGER 2] Testando tentativa do Agente B usar seleção implícita para aba do Agente A...');
// Se Agente B tem sua aba (201), targetId implícito deve resolver para 201, NUNCA 101
assert.equal(await access.targetId(null, 'agent_beta'), 201);
assert.equal(await access.targetId(undefined, 'agent_beta'), 201);

// Se Agente B não tiver abas registradas, não deve conseguir roubar a 101
registry.releaseTabFromSession(201);
await assert.rejects(
  access.targetId(null, 'agent_beta'),
  /TAB_SELECTION_REQUIRED/,
  'Agente sem abas alocadas não pode resolver aba de outro agente implicitamente'
);

console.log('[CHALLENGER 2] Testando agente anônimo (null, vazio, undefined) operando na aba de Alpha...');
const ANON_SESSIONS = [null, '', undefined];
for (const anon of ANON_SESSIONS) {
  assert.throws(
    () => registry.validateTabAccess(anon, 101),
    /TAB_ACCESS_DENIED: Sessão do agente não identificada\./,
    `Anônimo (${anon}) deve receber TAB_ACCESS_DENIED ao tentar acessar aba 101`
  );
  await assert.rejects(
    access.targetId(101, anon),
    /TAB_ACCESS_DENIED: Sessão do agente não identificada\./,
    `targetId deve rejeitar anônimo (${anon}) na aba 101`
  );
  await assert.rejects(
    access.requireGranted(101, anon),
    /TAB_ACCESS_DENIED: Sessão do agente não identificada\./,
    `requireGranted deve rejeitar anônimo (${anon}) na aba 101`
  );
}

console.log('[CHALLENGER 2] Testando anônimo em seleção implícita com aba do Agente A presente...');
// Adiciona aba 101 aos grants globais para simular tentativa extrema de sequestro anônimo
grants = [101];
await assert.rejects(
  access.targetId(null, null),
  /TAB_ACCESS_DENIED: Sessão do agente não identificada\./,
  'Seleção implícita anônima não pode acessar aba restrita a agente mesmo se estiver em grants'
);

console.log('[CHALLENGER 2] Sucesso: todas as tentativas de invasão foram bloqueadas com TAB_ACCESS_DENIED.');
