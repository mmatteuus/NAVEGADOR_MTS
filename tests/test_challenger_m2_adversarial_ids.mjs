/**
 * @file test_challenger_m2_adversarial_ids.mjs
 * @description Testes empíricos adversariais de forjamento de IDs e concorrência (Challenger 2).
 * Valida resistência contra IDs negativos, SQLi/strings, NaN, prototype pollution e race conditions.
 */
import assert from 'node:assert/strict';

let tabs = [{ id: 500, windowId: 1, title: 'Secure Tab', url: 'https://secure.test', active: true }];
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
registry.assignTabToSession('agent_alpha', 500);

console.log('[CHALLENGER 2] Testando injeção de IDs forjados e maliciosos...');
const MALICIOUS_TAB_IDS = [
  -1, -999, '101; DROP TABLE tabs;', 'NaN', NaN,
  '__proto__', 'constructor', 'prototype',
  { toString: () => 'malicious_id' }
];

for (const badId of MALICIOUS_TAB_IDS) {
  // Tentativa do Agente Beta com ID malicioso
  assert.throws(
    () => registry.validateTabAccess('agent_beta', badId),
    /TAB_ACCESS_DENIED/,
    `ID malicioso (${String(badId)}) deve ser rejeitado para outro agente`
  );

  // Tentativa do próprio Agente Alpha com ID não registrado
  assert.throws(
    () => registry.validateTabAccess('agent_alpha', badId),
    /TAB_ACCESS_DENIED/,
    `ID malicioso (${String(badId)}) não alocado deve ser rejeitado para Alpha`
  );

  // Tentativa via targetId
  await assert.rejects(
    access.targetId(badId, 'agent_beta'),
    /TAB_ACCESS_DENIED|TAB_NOT_ALLOWED/,
    `targetId deve rejeitar ID malicioso (${String(badId)})`
  );
}

console.log('[CHALLENGER 2] Testando blindagem contra Prototype Pollution...');
registry.assignTabToSession('__proto__', 777);
registry.assignTabToSession('constructor', 888);

// Verifica se propriedades globais foram poluídas
assert.strictEqual(Object.prototype.polluted, undefined, 'Object.prototype não pode ser poluído');
assert.strictEqual(Object.prototype[777], undefined, 'Object.prototype não deve conter ID numérico');

// Tentativa de sessão maliciosa acessar aba legítima do Alpha
assert.throws(
  () => registry.validateTabAccess('__proto__', 500),
  /TAB_ACCESS_DENIED/,
  'Sessão __proto__ não pode acessar abas legítimas de outros agentes'
);
assert.throws(
  () => registry.validateTabAccess('agent_alpha', 777),
  /TAB_ACCESS_DENIED/,
  'Agente Alpha não pode acessar aba registrada sob __proto__'
);

console.log('[CHALLENGER 2] Testando race condition em releaseTabFromSession com 50 requisições simultâneas...');
const CONCURRENT_REQUESTS = 50;
const attackPromises = [];

for (let i = 0; i < CONCURRENT_REQUESTS; i++) {
  attackPromises.push((async () => {
    // Intercala operações de validação e liberação
    if (i === 25) {
      registry.releaseTabFromSession(500);
    }
    try {
      registry.validateTabAccess('agent_beta', 500);
      return { allowed: true, index: i };
    } catch (err) {
      assert.match(err.message, /TAB_ACCESS_DENIED/);
      return { allowed: false, index: i, error: err.message };
    }
  })());
}

const attackResults = await Promise.all(attackPromises);
const allowedCount = attackResults.filter(r => r.allowed).length;

assert.strictEqual(allowedCount, 0, 'Zero requisições invasoras podem ser autorizadas durante liberação');
assert.strictEqual(registry.getSessionForTab(500), null, 'Aba 500 deve estar desalocada');

// Pós-liberação: Agente Beta tenta se apossar da aba liberada
assert.throws(
  () => registry.validateTabAccess('agent_beta', 500),
  /TAB_ACCESS_DENIED/,
  'Após liberação, Agente Beta ainda deve ter acesso negado à aba desvinculada'
);

console.log('[CHALLENGER 2] Sucesso: IDs maliciosos, prototype pollution e race conditions bloqueados.');
