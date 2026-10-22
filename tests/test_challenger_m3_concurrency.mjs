/**
 * @file test_challenger_m3_concurrency.mjs
 * @description Teste de estresse empírico e concorrência massiva para cookie_isolator.js.
 * Submete o isolador a rajadas concorrentes multi-agente, limpezas simultâneas e jitter I/O.
 */

import assert from 'node:assert';
import {
  getSessionCookies, setSessionCookie, clearSessionCookies,
  clearSessionStorage, setSessionLocalStorage, getSessionLocalStorage
} from '../src/extension/background/cookie_isolator.js';

const sleep = ms => new Promise(r => setTimeout(r, ms));
const chromeCookiesStore = new Map();

globalThis.chrome = {
  cookies: {
    async getAll(q) {
      await sleep(Math.floor(Math.random() * 4) + 1);
      const res = [];
      for (const c of chromeCookiesStore.values()) {
        if (q?.storeId && c.storeId !== q.storeId) continue;
        if (q?.name && c.name !== q.name) continue;
        res.push(c);
      }
      return res;
    },
    async set(details) {
      await sleep(Math.floor(Math.random() * 4) + 1);
      chromeCookiesStore.set(`${details.storeId || '0'}:${details.domain || ''}:${details.name}`, { ...details, storeId: details.storeId || '0' });
      return details;
    },
    async remove(details) {
      await sleep(Math.floor(Math.random() * 4) + 1);
      chromeCookiesStore.delete(`${details.storeId || '0'}:${details.url}:${details.name}`);
      return { success: true };
    },
    async getAllCookieStores() {
      await sleep(1);
      return [{ id: '0', tabIds: [] }, { id: '1', tabIds: [101] }];
    }
  }
};

async function testConcurrentBursts() {
  console.log('[CHALLENGER M3 - TEST 1] Rajada concorrente massiva (10 agentes x 20 cookies)...');
  const AGENT_COUNT = 10, COOKIE_COUNT = 20, domain = 'banco.seguro.corp';
  const tasks = [];

  for (let a = 0; a < AGENT_COUNT; a++) {
    const sid = `agent_${a}`;
    tasks.push((async () => {
      for (let i = 0; i < COOKIE_COUNT; i++) {
        await setSessionCookie(sid, { domain, name: `auth_session_${i}`, value: `secret_${sid}_val_${i}` });
      }
      const cookies = await getSessionCookies(sid, { domain, asDict: true });
      for (let i = 0; i < COOKIE_COUNT; i++) {
        assert.strictEqual(cookies[`auth_session_${i}`], `secret_${sid}_val_${i}`, `Valor incorreto na sessão ${sid}`);
      }
      for (const [k, v] of Object.entries(cookies)) {
        assert.ok(v.includes(`_${sid}_`), `VAZAMENTO CRÍTICO: ${sid} observou dado alheio: ${k}=${v}`);
      }
    })());
  }
  await Promise.all(tasks);
  console.log('  -> PASS: 200 cookies gravados/lidos simultaneamente sem colisão nem vazamento.');
}

async function testChaosClearAndConcurrentWrites() {
  console.log('[CHALLENGER M3 - TEST 2] Caos concorrente: gravações vs limpezas simultâneas...');
  const domain = 'app.financas.corp';
  const survivors = ['survivor_alpha', 'survivor_beta', 'survivor_gamma'];
  const victims = ['victim_one', 'victim_two', 'victim_three'];

  const runSurvivor = async (sid) => {
    for (let cycle = 0; cycle < 15; cycle++) {
      await setSessionCookie(sid, { domain, name: `key_${cycle}`, value: `val_${sid}_${cycle}` });
      setSessionLocalStorage(sid, `https://${domain}`, `ls_${cycle}`, `ls_val_${sid}_${cycle}`);
      await sleep(Math.floor(Math.random() * 3));
      const c = await getSessionCookies(sid, { domain, asDict: true });
      assert.strictEqual(c[`key_${cycle}`], `val_${sid}_${cycle}`);
    }
  };

  const runVictim = async (sid) => {
    for (let cycle = 0; cycle < 10; cycle++) {
      await setSessionCookie(sid, { domain, name: `vkey_${cycle}`, value: `victim_${sid}_${cycle}` });
      setSessionLocalStorage(sid, `https://${domain}`, `vls_${cycle}`, `ls_victim_${sid}`);
      if (cycle % 3 === 0) {
        await clearSessionCookies(sid, { domain });
        clearSessionStorage(sid);
      }
    }
    clearSessionStorage(sid);
    const postClearCookies = await getSessionCookies(sid, { domain });
    assert.strictEqual(postClearCookies.length, 0, `Cookies de ${sid} deveriam estar limpos`);
    assert.strictEqual(getSessionLocalStorage(sid, `https://${domain}`, 'vls_0'), null);
  };

  await Promise.all([...survivors.map(runSurvivor), ...victims.map(runVictim)]);

  for (const sid of survivors) {
    const c = await getSessionCookies(sid, { domain, asDict: true });
    assert.strictEqual(Object.keys(c).length, 15, `Sobrevivente ${sid} perdeu cookies por limpeza cruzada`);
    for (let i = 0; i < 15; i++) {
      assert.strictEqual(c[`key_${i}`], `val_${sid}_${i}`);
      assert.strictEqual(getSessionLocalStorage(sid, `https://${domain}`, `ls_${i}`), `ls_val_${sid}_${i}`);
    }
  }
  console.log('  -> PASS: Limpezas simultâneas em vítimas não perturbaram sobreviventes.');
}

async function testMalformedAndEdgeCases() {
  console.log('[CHALLENGER M3 - TEST 3] Concorrência com chamadas malformadas e fail-closed...');
  const badCalls = [
    setSessionCookie(null, { name: 'c', value: '1' }), setSessionCookie(undefined, { name: 'c', value: '1' }),
    setSessionCookie('', { name: 'c', value: '1' }), getSessionCookies(null),
    getSessionCookies(undefined), getSessionCookies(''), clearSessionCookies(null)
  ];
  for (const p of badCalls) await assert.rejects(async () => p, /SESSION_REQUIRED/);

  await assert.rejects(async () => setSessionCookie('agent_x', {}), /COOKIE_NAME_REQUIRED/);
  assert.strictEqual(setSessionLocalStorage(null, 'https://a.test', 'k', 'v'), false);
  assert.strictEqual(getSessionLocalStorage(null, 'https://a.test', 'k'), null);
  assert.throws(() => clearSessionStorage(null), /SESSION_REQUIRED/);
  console.log('  -> PASS: Todas as chamadas inválidas rejeitadas com Fail-Closed sem vazamento.');
}

async function main() {
  console.log('=== INICIANDO DESAFIO ADVERSARIAL EMPÍRICO M3 (CONCORRÊNCIA) ===\n');
  await testConcurrentBursts();
  await testChaosClearAndConcurrentWrites();
  await testMalformedAndEdgeCases();
  console.log('\n=== [VEREDITO EMPÍRICO M3]: APROVADO COM 100% DE SUCESSO ===');
  process.exit(0);
}

main().catch(err => {
  console.error('\n[FALHA NO DESAFIO EMPÍRICO M3]:', err);
  process.exit(1);
});
