/**
 * @file test_challenger_m2_queues.mjs
 * @description Testes de estresse adversarial para as filas concorrentes em session_queues.js.
 * Verifica ordem FIFO, isolamento de atraso entre sessões e resiliência a rejeições.
 */

import assert from 'node:assert';
import {
  enqueueSessionCommand,
  removeSessionQueue,
  clearAllSessionQueues,
  getActiveQueueCount
} from '../src/extension/background/session_queues.js';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function testFifoStrictOrdering() {
  console.log('[TEST 1] Ordem FIFO rigorosa sob tempos de execução inversos...');
  clearAllSessionQueues();
  const completionOrder = [];
  const total = 25;

  const promises = [];
  for (let i = 0; i < total; i++) {
    // Tarefas anteriores demoram mais que posteriores para forçar inversão se não houver FIFO
    const delay = Math.max(2, (total - i) * 2);
    promises.push(
      enqueueSessionCommand('agent_fifo', async () => {
        await sleep(delay);
        completionOrder.push(i);
        return i;
      })
    );
  }

  await Promise.all(promises);
  assert.strictEqual(completionOrder.length, total);
  for (let i = 0; i < total; i++) {
    assert.strictEqual(completionOrder[i], i, `Esperado item ${i} na posição ${i}, obtido ${completionOrder[i]}`);
  }
  console.log('  -> PASS: Todas as 25 tarefas executaram em ordem FIFO estrita.');
}

async function testCrossSessionIsolationAndErrorResilience() {
  console.log('[TEST 2] Isolamento de atraso e não-bloqueio entre Agente Alpha e Beta...');
  clearAllSessionQueues();

  let alphaStarted = false;
  let alphaFinished = false;
  let betaAllFinishedTime = null;
  const start = Date.now();

  // Alpha enfileira tarefa demorada de 100ms que rejeita
  const alphaPromise = enqueueSessionCommand('agent_alpha', async () => {
    alphaStarted = true;
    await sleep(100);
    alphaFinished = true;
    throw new Error('Falha catastrófica simulada em Alpha');
  });

  // Beta enfileira 5 tarefas rápidas (5ms cada)
  const betaPromises = [];
  for (let i = 0; i < 5; i++) {
    betaPromises.push(
      enqueueSessionCommand('agent_beta', async () => {
        await sleep(5);
        return `beta_${i}`;
      })
    );
  }

  // Beta deve completar bem antes de Alpha
  const betaResults = await Promise.all(betaPromises);
  betaAllFinishedTime = Date.now() - start;

  assert.strictEqual(betaResults.length, 5);
  assert.ok(betaAllFinishedTime < 80, `Beta levou ${betaAllFinishedTime}ms, deveria terminar bem antes dos 100ms de Alpha`);
  assert.strictEqual(alphaFinished, false, 'Beta terminou antes de Alpha terminar sua tarefa lenta');

  // Agora aguarda a rejeição de Alpha
  await assert.rejects(alphaPromise, /Falha catastrófica simulada em Alpha/);
  console.log(`  -> PASS: Beta concluiu em ${betaAllFinishedTime}ms sem esperar Alpha (100ms).`);

  console.log('[TEST 3] Recuperação imediata da fila de Alpha após erro...');
  // O próximo comando de Alpha deve executar sem ser bloqueado pela rejeição anterior
  const alphaRecovery = await enqueueSessionCommand('agent_alpha', async () => {
    return 'alpha_recuperado';
  });
  assert.strictEqual(alphaRecovery, 'alpha_recuperado');
  console.log('  -> PASS: Fila de Alpha recuperou e executou comando subsequente.');
}

async function testHighConcurrencyInterleavedBurst() {
  console.log('[TEST 4] Rajada concorrente intercalada entre Alpha, Beta e Gamma (90 comandos)...');
  clearAllSessionQueues();

  const sessions = ['alpha', 'beta', 'gamma'];
  const logs = { alpha: [], beta: [], gamma: [] };
  const allPromises = [];

  for (let i = 0; i < 30; i++) {
    for (const s of sessions) {
      const idx = i;
      allPromises.push(
        enqueueSessionCommand(`agent_${s}`, async () => {
          await sleep(Math.floor(Math.random() * 4) + 1);
          logs[s].push(idx);
          return `${s}_${idx}`;
        })
      );
    }
  }

  const results = await Promise.all(allPromises);
  assert.strictEqual(results.length, 90);
  assert.strictEqual(getActiveQueueCount(), 3);

  // Cada sessão deve ter preservado sua ordem sequencial local 0..29
  for (const s of sessions) {
    assert.strictEqual(logs[s].length, 30);
    for (let i = 0; i < 30; i++) {
      assert.strictEqual(logs[s][i], i, `Sessão ${s} violou FIFO no índice ${i}`);
    }
  }

  removeSessionQueue('agent_alpha');
  assert.strictEqual(getActiveQueueCount(), 2);
  clearAllSessionQueues();
  assert.strictEqual(getActiveQueueCount(), 0);
  console.log('  -> PASS: 90 comandos intercalados processados com FIFO rigoroso por agente.');
}

async function runAll() {
  await testFifoStrictOrdering();
  await testCrossSessionIsolationAndErrorResilience();
  await testHighConcurrencyInterleavedBurst();
  console.log('\n[SUCESSO] Todos os testes de estresse em session_queues.js passaram!');
}

runAll().catch(err => {
  console.error('\n[FALHA ADVERSARIAL]', err);
  process.exit(1);
});
