/**
 * @file test_e2e_real_multisession.mjs
 * @description Teste E2E multissessão com Chromium real (Playwright): isolamento de
 * cookies/storage, segregação de abas, bloqueio cruzado e concorrência.
 */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { createTestHttpServer } from './fixture_http_server.mjs';
import { launchAgentContext } from './fixture_chromium_context.mjs';
import { MCPAgentClient } from './mcp_agent_client.mjs';

async function waitForBridge(url, maxWaitMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    try {
      const res = await fetch(`${url}/bridge-status`);
      if (res.ok && (await res.json()).connected) return true;
    } catch (_) {}
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error('Extensão não conectou à bridge WebSocket no prazo.');
}

async function runE2ERealMultisession() {
  console.log('--- [1/6] Inicializando Servidor HTTP e Bridge MCP ---');
  const httpFixture = await createTestHttpServer().start();
  const pyBridge = spawn('python', ['tests/e2e_real/fixture_mcp_bridge.py'], {
    windowsHide: true, stdio: ['ignore', 'pipe', 'pipe']
  });
  pyBridge.stderr.on('data', d => console.error('[PY-ERR]', d.toString()));

  const bridgeInfo = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Timeout iniciando fixture_mcp_bridge.py')), 15000);
    createInterface({ input: pyBridge.stdout }).once('line', l => { clearTimeout(timer); resolve(JSON.parse(l)); });
  });

  console.log(`Bridge WS: ${bridgeInfo.wsPort} | MCP HTTP: ${bridgeInfo.mcpUrl} | HTTP QA: ${httpFixture.url}`);
  const clientA = new MCPAgentClient(bridgeInfo.mcpUrl, 'agent-a');
  const clientB = new MCPAgentClient(bridgeInfo.mcpUrl, 'agent-b');
  await clientA.initialize();
  await clientB.initialize();

  console.log('--- [2/6] Lançando Contextos Chromium Reais (A e B) ---');
  const ctxA = await launchAgentContext({ sessionId: 'agent_a', wsPort: bridgeInfo.wsPort, loadExtension: true });
  const ctxB = await launchAgentContext({ sessionId: 'agent_b', wsPort: null, loadExtension: false });
  await waitForBridge(bridgeInfo.mcpUrl);

  try {
    console.log('--- [3/6] Teste 1: Autenticação e Gravação de Storage em A ---');
    const pageA = await ctxA.context.newPage();
    await pageA.goto(`${httpFixture.url}/agent-a/set-auth`);
    await pageA.waitForSelector('#auth-status');
    assert.equal(await pageA.evaluate(() => localStorage.getItem('agent_storage_key')), 'ALPHA_STORAGE_SECRET_888');

    console.log('--- [4/6] Teste 2: Isolamento Físico de Cookies e Storage em B ---');
    const pageB = await ctxB.context.newPage();
    await pageB.goto(`${httpFixture.url}/agent-b/check-auth`);
    await pageB.waitForSelector('#cookie-leak');
    assert.equal(await pageB.$eval('#cookie-leak', el => el.textContent), 'CLEAN');
    assert.equal(await pageB.$eval('#storage-leak', el => el.textContent), 'CLEAN');
    assert.equal(httpFixture.stats.cookiesReceivedInB.length, 0);

    console.log('--- [5/6] Teste 3 & 4: Segregação e Bloqueio de Acesso Cruzado ---');
    const newTabRes = await clientA.callTool('browser_manage_tabs', {
      action: 'new', url: `${httpFixture.url}/agent-a/set-auth`
    });
    assert.equal(newTabRes.isError, false, JSON.stringify(newTabRes));
    const tabIdA = newTabRes.data?.tabId || newTabRes.data?.id;
    assert.ok(tabIdA, 'Aba do Agente A deve possuir ID válido');

    const readAdv = await clientB.callTool('browser_get_text', { tabId: tabIdA });
    assert.equal(readAdv.isError, true);
    assert.match(readAdv.error, /Acesso recusado|TAB_ACCESS_DENIED|BROWSER_SELECTION_REQUIRED/);

    const snapAdv = await clientB.callTool('browser_screenshot', { tabId: tabIdA });
    assert.equal(snapAdv.isError, true);
    assert.match(snapAdv.error, /Acesso recusado|TAB_ACCESS_DENIED|BROWSER_SELECTION_REQUIRED/);

    const closeAdv = await clientB.callTool('browser_manage_tabs', { action: 'close', tabId: tabIdA });
    assert.equal(closeAdv.isError, true);
    assert.match(closeAdv.error, /Acesso recusado|TAB_ACCESS_DENIED|BROWSER_SELECTION_REQUIRED/);

    const closeLegit = await clientA.callTool('browser_manage_tabs', { action: 'close', tabId: tabIdA });
    assert.equal(closeLegit.isError, false);

    console.log('--- [6/6] Teste 5: Burst Concorrente Multissessão (20 chamadas) ---');
    const burstPromises = [];
    for (let i = 0; i < 10; i++) {
      burstPromises.push(clientA.callTool('browser_manage_tabs', { action: 'list' }));
      burstPromises.push(clientB.callTool('browser_manage_tabs', { action: 'list' }));
    }
    const results = await Promise.all(burstPromises);
    assert.equal(results.length, 20);
    assert.ok(results.every(r => r.isError === false), 'Todos os comandos concorrentes devem passar');

    console.log('\n======================================================');
    console.log('SUCESSO TOTAL! 5 CENÁRIOS E2E REAL APROVADOS COM LOUVOR!');
    console.log('======================================================');
  } finally {
    await ctxA.close();
    await ctxB.close();
    await fetch(`${bridgeInfo.mcpUrl}/stop`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
    }).catch(() => {});
    pyBridge.kill();
    await httpFixture.stop();
  }
}

runE2ERealMultisession().catch(err => {
  console.error('\n[FALHA FATAL NO TESTE E2E REAL]', err);
  process.exit(1);
});
