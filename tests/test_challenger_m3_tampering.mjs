/**
 * @file test_challenger_m3_tampering.mjs
 * @description Testes adversariais de violação, injeção e adulteração de cookies/storage (Challenger M3).
 */
import assert from 'node:assert/strict';

const sentWs = [];
globalThis.WebSocket = class {
  static OPEN = 1;
  constructor() { this.readyState = 1; setTimeout(() => this.onopen?.(), 2); }
  send(d) { sentWs.push(JSON.parse(d)); }
  close() { this.readyState = 3; this.onclose?.(); }
};
globalThis.chrome = {
  runtime: { getURL: p => `chrome-extension://test/${p}` },
  storage: {
    local: { get: async () => ({ browser_mts_automation_enabled: true }), set: async () => {} },
    session: { get: async () => ({ browser_mts_session_tab_grants: [100] }), set: async () => {} }
  },
  tabs: { query: async () => [{ id: 100, active: true, url: 'https://corp.test' }], get: async id => ({ id: Number(id) }) },
  cookies: { getAll: async () => [], set: async () => {}, remove: async () => {}, getAllCookieStores: async () => [{ id: '0', tabIds: [100] }] }
};

const isolator = await import('../src/extension/background/cookie_isolator.js');
const { connectWebSocket } = await import('../src/extension/background/ws_client.js');
const { dispatchIncomingCommand } = await import('../src/extension/background/command_dispatcher.js');

const waitMsg = async (n, t = 1500) => {
  const s = Date.now();
  while (sentWs.length < n && Date.now() - s < t) await new Promise(r => setTimeout(r, 5));
};

async function testSessionIdInjection() {
  console.log('[CHALLENGER 3] 1. Injeção de sessionId (nulo, vazio, traversal, prototype)...');
  for (const bad of [null, undefined, '']) {
    await assert.rejects(async () => isolator.getSessionCookies(bad), /SESSION_REQUIRED/);
    await assert.rejects(async () => isolator.setSessionCookie(bad, { name: 'c' }), /SESSION_REQUIRED/);
    await assert.rejects(async () => isolator.clearSessionCookies(bad), /SESSION_REQUIRED/);
    assert.throws(() => isolator.clearSessionStorage(bad), /SESSION_REQUIRED/);
    assert.strictEqual(isolator.setSessionLocalStorage(bad, 'https://test.corp', 'k', 'v'), false);
    assert.strictEqual(isolator.getSessionLocalStorage(bad, 'https://test.corp', 'k'), null);
  }

  await isolator.setSessionCookie('agent_legit', { domain: 'bank.corp', name: 'tok', value: 'SEC_LEGIT' });
  await isolator.setSessionCookie('../../agent_legit', { domain: 'bank.corp', name: 'tok', value: 'SEC_TRAVERSAL' });
  await isolator.setSessionCookie('__proto__', { domain: 'bank.corp', name: 'tok', value: 'SEC_PROTO' });

  assert.strictEqual(Object.prototype.polluted, undefined, 'Object.prototype não pode ser poluído');
  assert.strictEqual(Object.prototype.tok, undefined, 'Chave de cookie não deve vazar para Object.prototype');

  const legitTok = (await isolator.getSessionCookies('agent_legit', { domain: 'bank.corp', asDict: true })).tok;
  const travTok = (await isolator.getSessionCookies('../../agent_legit', { domain: 'bank.corp', asDict: true })).tok;
  assert.strictEqual(legitTok, 'SEC_LEGIT', 'Traversal não deve contaminar sessão legítima');
  assert.strictEqual(travTok, 'SEC_TRAVERSAL', 'Traversal mantido em partição literal isolada');

  isolator.clearSessionStorage('../../agent_legit');
  assert.strictEqual((await isolator.getSessionCookies('agent_legit', { domain: 'bank.corp', asDict: true })).tok, 'SEC_LEGIT');
  console.log('  -> PASS: Rejeição fail-closed de IDs inválidos e isolamento de path traversal.');
}

async function testCrossAgentTampering() {
  console.log('[CHALLENGER 3] 2. Tentativa de sobrescrita e deleção cruzada de cookies...');
  await isolator.setSessionCookie('agent_alpha', { domain: 'app.corp', name: 'auth_key', value: 'ALPHA_GOLD' });

  const betaRead = await isolator.getSessionCookies('agent_beta', { domain: 'app.corp' });
  assert.strictEqual(betaRead.length, 0, 'Beta não deve ler cookies do Alpha');

  await isolator.setSessionCookie('agent_beta', { domain: 'app.corp', name: 'auth_key', value: 'BETA_POISON' });
  assert.strictEqual((await isolator.getSessionCookies('agent_alpha', { domain: 'app.corp', asDict: true })).auth_key, 'ALPHA_GOLD');
  assert.strictEqual((await isolator.getSessionCookies('agent_beta', { domain: 'app.corp', asDict: true })).auth_key, 'BETA_POISON');

  await isolator.clearSessionCookies('agent_beta', { domain: 'app.corp', name: 'auth_key' });
  assert.strictEqual((await isolator.getSessionCookies('agent_alpha', { domain: 'app.corp', asDict: true })).auth_key, 'ALPHA_GOLD');
  assert.strictEqual((await isolator.getSessionCookies('agent_beta', { domain: 'app.corp', asDict: true })).auth_key, undefined);

  isolator.clearSessionStorage('agent_beta');
  assert.strictEqual((await isolator.getSessionCookies('agent_alpha', { domain: 'app.corp', asDict: true })).auth_key, 'ALPHA_GOLD');
  console.log('  -> PASS: Sobrescrita, remoção e purga de sessão por Beta não afetaram Alpha.');
}

async function testLocalStorageTampering() {
  console.log('[CHALLENGER 3] 3. Tentativas de contaminação cruzada de localStorage...');
  isolator.setSessionLocalStorage('agent_alpha', 'https://app.corp', 'jwt', 'JWT_ALPHA');

  assert.strictEqual(isolator.getSessionLocalStorage('agent_beta', 'https://app.corp', 'jwt'), null);
  isolator.setSessionLocalStorage('agent_beta', 'https://app.corp', 'jwt', 'JWT_BETA');
  assert.strictEqual(isolator.getSessionLocalStorage('agent_alpha', 'https://app.corp', 'jwt'), 'JWT_ALPHA');

  isolator.setSessionLocalStorage('../../agent_alpha', 'https://app.corp', 'jwt', 'JWT_TRAVERSAL');
  assert.strictEqual(isolator.getSessionLocalStorage('agent_alpha', 'https://app.corp', 'jwt'), 'JWT_ALPHA');

  isolator.setSessionLocalStorage('agent_beta', 'https://app.corp', '__proto__', 'polluted');
  assert.strictEqual(Object.prototype.polluted, undefined);
  console.log('  -> PASS: LocalStorage particionado com imunidade a vazamento e poluição.');
}

async function testDispatcherFailClosed() {
  console.log('[CHALLENGER 3] 4. Disparo via command_dispatcher sem sessionId (Fail-Closed)...');
  sentWs.length = 0;
  const actions = ['browser_get_cookies', 'browser_set_cookie', 'browser_clear_cookies', 'browser_clear_storage'];
  actions.forEach((act, idx) => dispatchIncomingCommand({ id: `fc_${idx}`, action: act, payload: { domain: 'test.corp' } }));

  await waitMsg(4);
  assert.strictEqual(sentWs.length, 4);
  for (const resp of sentWs) {
    assert.strictEqual(resp.success, false, `Ação ${resp.id} sem sessionId deve falhar`);
    assert.match(resp.error, /SESSION_REQUIRED/);
  }

  dispatchIncomingCommand({ id: 'fc_clear_beta', sessionId: 'agent_beta', action: 'browser_clear_cookies', payload: { domain: 'app.corp' } });
  await waitMsg(5);
  assert.strictEqual((await isolator.getSessionCookies('agent_alpha', { domain: 'app.corp', asDict: true })).auth_key, 'ALPHA_GOLD');
  console.log('  -> PASS: Dispatcher rejeita requisições sem sessionId e isola limpezas.');
}

async function testConcurrentTamperingBurst() {
  console.log('[CHALLENGER 3] 5. Rajada concorrente de adulteração simultânea (40 operações)...');
  const ops = [];
  for (let i = 0; i < 40; i++) {
    ops.push((async () => {
      if (i % 2 === 0) {
        await isolator.setSessionCookie(`evil_${i}`, { domain: 'app.corp', name: 'auth_key', value: `EVIL_${i}` });
        await isolator.clearSessionCookies(`evil_${i}`, { domain: 'app.corp' });
      } else {
        const cookies = await isolator.getSessionCookies('agent_alpha', { domain: 'app.corp', asDict: true });
        assert.strictEqual(cookies.auth_key, 'ALPHA_GOLD', `Alpha corrompido no ciclo ${i}`);
      }
    })());
  }
  await Promise.all(ops);
  console.log('  -> PASS: Integridade do Agente Alpha preservada sob rajada de mutações concorrentes.');
}

async function run() {
  await connectWebSocket();
  await new Promise(r => setTimeout(r, 20));
  await testSessionIdInjection();
  await testCrossAgentTampering();
  await testLocalStorageTampering();
  await testDispatcherFailClosed();
  await testConcurrentTamperingBurst();
  console.log('\n[CHALLENGER 3 APROVADO] Barreiras de isolamento de cookies e storage comprovadas intransponíveis!');
  process.exit(0);
}

run().catch(err => {
  console.error('\n[CHALLENGER 3 FALHOU]', err);
  process.exit(1);
});
