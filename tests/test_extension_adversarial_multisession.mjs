/**
 * @file test_extension_adversarial_multisession.mjs
 * @description Suíte de testes adversariais para Extensão MV3 com foco em multissessão
 * e isolamento estrito de abas (TAB_ACCESS_DENIED) entre múltiplos agentes.
 */

import assert from 'node:assert';

const sessionTabRegistry = new Map();
const openTabs = [
  { id: 101, url: 'https://site-alpha.test', windowId: 10 },
  { id: 102, url: 'https://doc-alpha.test', windowId: 10 },
  { id: 201, url: 'https://site-beta.test', windowId: 20 },
  { id: 202, url: 'https://doc-beta.test', windowId: 20 }
];

sessionTabRegistry.set('agent_alpha', new Set([101, 102]));
sessionTabRegistry.set('agent_beta', new Set([201, 202]));

function validateTabAccess(sessionId, tabId) {
  if (!sessionId) {
    throw new Error('TAB_ACCESS_DENIED: Sessão do agente não identificada.');
  }
  const granted = sessionTabRegistry.get(sessionId);
  if (!granted || !granted.has(Number(tabId))) {
    throw new Error('TAB_ACCESS_DENIED: A aba solicitada não pertence à sessão do agente.');
  }
  const exists = openTabs.some(t => t.id === Number(tabId));
  if (!exists) {
    throw new Error('TAB_NOT_FOUND: Aba informada não existe.');
  }
  return true;
}

async function dispatchMultisessionCommand(message) {
  const reqId = message.id || `cmd_${Date.now()}`;
  const sessionId = message.sessionId || message.payload?.sessionId;
  const action = message.action || message.type || '';
  const params = message.payload || message.params || {};
  const tabId = params.tabId;

  try {
    if (tabId !== undefined && tabId !== null) {
      validateTabAccess(sessionId, tabId);
    }
    return {
      id: reqId,
      sessionId,
      type: 'action_response',
      success: true,
      payload: { action, tabId, executed: true },
      error: null
    };
  } catch (err) {
    return {
      id: reqId,
      sessionId,
      type: 'action_response',
      success: false,
      payload: null,
      error: err.message
    };
  }
}

async function runMultisessionAdversarialTests() {
  console.log('[TEST 1] Operações legítimas e concorrentes em abas exclusivas...');
  const resAlpha = await dispatchMultisessionCommand({
    id: 'cmd_a_1', sessionId: 'agent_alpha', action: 'browser_get_text', payload: { tabId: 101 }
  });
  const resBeta = await dispatchMultisessionCommand({
    id: 'cmd_b_1', sessionId: 'agent_beta', action: 'browser_get_text', payload: { tabId: 201 }
  });
  assert.strictEqual(resAlpha.success, true);
  assert.strictEqual(resBeta.success, true);
  console.log('  -> PASS: Ambas as sessões operaram em suas respectivas abas.');

  console.log('[TEST 2] Tentativa adversarial de leitura cruzada (Alpha -> Aba 201 de Beta)...');
  const crossRead = await dispatchMultisessionCommand({
    id: 'adv_read', sessionId: 'agent_alpha', action: 'browser_get_text', payload: { tabId: 201 }
  });
  assert.strictEqual(crossRead.success, false);
  assert.match(crossRead.error, /TAB_ACCESS_DENIED/);
  console.log('  -> PASS: Leitura cruzada rejeitada com TAB_ACCESS_DENIED.');

  console.log('[TEST 3] Tentativa adversarial de fechamento cruzado (Beta -> Aba 101 de Alpha)...');
  const crossClose = await dispatchMultisessionCommand({
    id: 'adv_close', sessionId: 'agent_beta', action: 'browser_close_tab', payload: { tabId: 101 }
  });
  assert.strictEqual(crossClose.success, false);
  assert.match(crossClose.error, /TAB_ACCESS_DENIED/);
  console.log('  -> PASS: Fechamento cruzado rejeitado com TAB_ACCESS_DENIED.');

  console.log('[TEST 4] Requisição sem sessionId operando em aba restrita...');
  const unauth = await dispatchMultisessionCommand({
    id: 'unauth_cmd', action: 'browser_click', payload: { tabId: 102 }
  });
  assert.strictEqual(unauth.success, false);
  assert.match(unauth.error, /TAB_ACCESS_DENIED/);
  console.log('  -> PASS: Comando sem identificador bloqueado.');

  console.log('[TEST 5] Burst concorrente de 20 comandos paralelos com segregação...');
  const promises = [];
  for (let i = 0; i < 10; i++) {
    promises.push(dispatchMultisessionCommand({
      id: `burst_a_${i}`, sessionId: 'agent_alpha', action: 'browser_scroll', payload: { tabId: 101 }
    }));
    promises.push(dispatchMultisessionCommand({
      id: `burst_b_${i}`, sessionId: 'agent_beta', action: 'browser_scroll', payload: { tabId: 202 }
    }));
  }
  const burstResults = await Promise.all(promises);
  assert.strictEqual(burstResults.length, 20);
  assert.ok(burstResults.every(r => r.success === true));
  console.log('  -> PASS: 20 requisições simultâneas segregadas sem interferência.');

  console.log('\n[SUCESSO] Suíte adversarial multissessão aprovada com louvor!');
  process.exit(0);
}

runMultisessionAdversarialTests().catch(err => {
  console.error('[FALHA NO TESTE MULTISSESSÃO]', err);
  process.exit(1);
});
