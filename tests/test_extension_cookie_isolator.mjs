/**
 * @file test_extension_cookie_isolator.mjs
 * @description Suíte de testes automatizados para cookie_isolator.js e isolamento de armazenamento MV3.
 */

import assert from 'node:assert';
import {
  getSessionCookies, setSessionCookie, clearSessionCookies,
  clearSessionStorage, setSessionLocalStorage, getSessionLocalStorage
} from '../src/extension/background/cookie_isolator.js';

async function runCookieIsolatorTests() {
  console.log('[TEST 1] Isolamento estrito de cookies entre múltiplos agentes...');
  await setSessionCookie('agent_alpha', { domain: 'corp.test', name: 'auth_token', value: 'secret_alpha_123' });
  await setSessionCookie('agent_alpha', { domain: 'corp.test', name: 'user_id', value: 'usr_alpha' });

  const cookiesBeta = await getSessionCookies('agent_beta', { domain: 'corp.test' });
  assert.strictEqual(cookiesBeta.length, 0, 'Vazamento: Agente Beta acessou cookies do Agente Alpha!');

  await setSessionCookie('agent_beta', { domain: 'corp.test', name: 'auth_token', value: 'secret_beta_456' });
  const alphaCookies = await getSessionCookies('agent_alpha', { domain: 'corp.test', asDict: true });
  const betaCookies = await getSessionCookies('agent_beta', { domain: 'corp.test', asDict: true });

  assert.strictEqual(alphaCookies['auth_token'], 'secret_alpha_123');
  assert.strictEqual(betaCookies['auth_token'], 'secret_beta_456');
  console.log('  -> PASS: Cookies gravados e consultados em partições estritamente isoladas.');

  console.log('[TEST 2] Particionamento de localStorage por sessão...');
  setSessionLocalStorage('agent_alpha', 'https://fin.test', 'api_key', 'key_alpha');
  setSessionLocalStorage('agent_beta', 'https://fin.test', 'api_key', 'key_beta');

  assert.strictEqual(getSessionLocalStorage('agent_alpha', 'https://fin.test', 'api_key'), 'key_alpha');
  assert.strictEqual(getSessionLocalStorage('agent_beta', 'https://fin.test', 'api_key'), 'key_beta');
  assert.strictEqual(getSessionLocalStorage('agent_gamma', 'https://fin.test', 'api_key'), null);
  console.log('  -> PASS: localStorage particionado com sucesso sem vazamento.');

  console.log('[TEST 3] Proteção contra mutação/remoção cruzada de cookies...');
  await clearSessionCookies('agent_beta', { domain: 'corp.test', name: 'auth_token' });
  const alphaAfterBetaClear = await getSessionCookies('agent_alpha', { domain: 'corp.test', asDict: true });
  const betaAfterClear = await getSessionCookies('agent_beta', { domain: 'corp.test', asDict: true });

  assert.strictEqual(alphaAfterBetaClear['auth_token'], 'secret_alpha_123');
  assert.strictEqual(betaAfterClear['auth_token'], undefined);
  console.log('  -> PASS: Remoção de cookie por Beta não afetou dados do Alpha.');

  console.log('[TEST 4] Limpeza atômica de sessão preservando sessões irmãs...');
  await setSessionCookie('agent_alpha', { domain: 'banco.test', name: 'sess', value: 'a' });
  await setSessionCookie('agent_beta', { domain: 'banco.test', name: 'sess', value: 'b' });
  setSessionLocalStorage('agent_alpha', 'https://banco.test', 'state', 'state_a');
  setSessionLocalStorage('agent_beta', 'https://banco.test', 'state', 'state_b');

  clearSessionStorage('agent_alpha');
  const alphaCleared = await getSessionCookies('agent_alpha', { domain: 'banco.test' });
  const betaPreserved = await getSessionCookies('agent_beta', { domain: 'banco.test', asDict: true });

  assert.strictEqual(alphaCleared.length, 0);
  assert.strictEqual(getSessionLocalStorage('agent_alpha', 'https://banco.test', 'state'), null);
  assert.strictEqual(betaPreserved['sess'], 'b');
  assert.strictEqual(getSessionLocalStorage('agent_beta', 'https://banco.test', 'state'), 'state_b');
  console.log('  -> PASS: Limpeza de Alpha preservou 100% dos dados de Beta.');

  console.log('[TEST 5] Rejeição de chamadas sem sessionId (Fail-Closed)...');
  await assert.rejects(async () => getSessionCookies(null), /SESSION_REQUIRED/);
  await assert.rejects(async () => setSessionCookie('', { name: 'c' }), /SESSION_REQUIRED/);
  assert.throws(() => clearSessionStorage(null), /SESSION_REQUIRED/);
  console.log('  -> PASS: Operações sem identificador de sessão rejeitadas com erro explícito.');

  console.log('\n[SUCESSO] Todos os testes de isolamento de cookies e storage passaram com louvor!');
  process.exit(0);
}

runCookieIsolatorTests().catch(err => {
  console.error('[FALHA NO TESTE DE COOKIES]', err);
  process.exit(1);
});
