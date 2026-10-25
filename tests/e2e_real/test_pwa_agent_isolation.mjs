/** E2E opt-in: PWA real, Service Worker offline e duas atribuições MCP. */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { createPwaFixture } from './pwa_fixture.mjs';
import { launchAgentContext } from './fixture_chromium_context.mjs';
import { MCPAgentClient } from './mcp_agent_client.mjs';

if (process.env.RUN_PWA_AGENT_E2E !== '1') {
  console.log('SKIP: defina RUN_PWA_AGENT_E2E=1 para Chromium real.'); process.exit(0);
}
const pwa = createPwaFixture();
const child = spawn(process.env.QA_PYTHON || 'python', ['tests/e2e_real/fixture_mcp_bridge.py'], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
child.stderr.on('data', data => process.stderr.write(`[bridge] ${data}`));
let info = null, ctx = null, pwaInfo = null, pwaStarted = false;
const stop = async () => {
  if (ctx) await ctx.close().catch(() => {});
  if (info?.mcpUrl) await fetch(`${info.mcpUrl}/stop`, { method: 'POST' }).catch(() => {});
  if (pwaStarted) await pwa.stop().catch(() => {});
  child.kill();
};
try {
  info = JSON.parse(await Promise.race([
    new Promise(resolve => createInterface({ input: child.stdout }).once('line', resolve)),
    new Promise((_, reject) => setTimeout(() => reject(new Error('bridge timeout')), 30000))
  ]));
  pwaInfo = await pwa.start(); pwaStarted = true;
  const a = new MCPAgentClient(info.mcpUrl, 'agent-a'), b = new MCPAgentClient(info.mcpUrl, 'agent-b');
  await a.initialize(); await b.initialize();
  ctx = await launchAgentContext({ sessionId: 'pwa-qa', wsPort: info.wsPort, loadExtension: true });
  const pageA = await ctx.context.newPage(), pageB = await ctx.context.newPage();
  for (const page of [pageA, pageB]) await (await ctx.context.newCDPSession(page)).send('Network.setCacheDisabled', { cacheDisabled: true });
  await pageA.goto(`${pwaInfo.url}agent-a`); await pageB.goto(`${pwaInfo.url}agent-b`);
  await Promise.all([pageA.evaluate(() => navigator.serviceWorker.ready), pageB.evaluate(() => navigator.serviceWorker.ready)]);
  await Promise.all([pageA.reload(), pageB.reload()]);
  assert.equal(await pageA.evaluate(() => !!navigator.serviceWorker.controller), true);
  assert.deepEqual(await pageA.evaluate(() => fetch('/manifest.json').then(r => r.json()).then(m => [m.name, m.display])), ['PWA QA', 'standalone']);
  const popup = await ctx.context.newPage(); await popup.goto(`chrome-extension://${ctx.extensionId}/popup/popup.html`);
  await popup.locator('#tab-access-list input').first().waitFor({ timeout: 15000 });
  const tabs = await ctx.worker.evaluate(() => chrome.tabs.query({}));
  const tabA = tabs.find(t => t.url === `${pwaInfo.url}agent-a`).id, tabB = tabs.find(t => t.url === `${pwaInfo.url}agent-b`).id;
  for (const [tabId, sid] of [[tabA, 'agent-a'], [tabB, 'agent-b']]) {
    await popup.locator(`#tab-access-list input[value="${tabId}"]`).check();
    await popup.locator(`select[data-tab-id="${tabId}"]`).selectOption(sid);
  }
  await popup.locator('#save-tab-grants').click();
  await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('salva'));
  assert.equal((await b.callTool('browser_get_text', { tabId: tabA })).isError, true);
  await pwa.stop();
  pwaStarted = false;
  await Promise.all([pageA.reload(), pageB.reload()]);
  assert.match(await pageA.title(), /PWA QA/); assert.match(await pageB.title(), /PWA QA/);
  await Promise.all([pageA, pageB].map(p => p.locator('#user').focus()));
  await Promise.all([pageA, pageB].map(p => p.locator('#user').selectText()));
  const before = await Promise.all([pageA, pageB].map(p => p.evaluate(() => ({
    activeId: document.activeElement?.id, selectionStart: document.activeElement?.selectionStart,
    selectionEnd: document.activeElement?.selectionEnd, user: document.querySelector('#user').value
  }))));
  const activeBefore = await ctx.worker.evaluate(() => chrome.tabs.query({}).then(ts => ts.map(t => [t.id, !!t.active])));
  const replies = await Promise.all([a.callTool('browser_type', { tabId: tabA, selector: '#agent', text: 'A' }), b.callTool('browser_type', { tabId: tabB, selector: '#agent', text: 'B' })]);
  assert.ok(replies.every(r => !r.isError), JSON.stringify(replies));
  assert.deepEqual(await Promise.all([pageA, pageB].map(p => p.evaluate(() => ({
    activeId: document.activeElement?.id, selectionStart: document.activeElement?.selectionStart,
    selectionEnd: document.activeElement?.selectionEnd, user: document.querySelector('#user').value
  })))), before);
  assert.deepEqual(await ctx.worker.evaluate(() => chrome.tabs.query({}).then(ts => ts.map(t => [t.id, !!t.active]))), activeBefore);
  assert.equal(await pageA.locator('#agent').inputValue(), 'A'); assert.equal(await pageB.locator('#agent').inputValue(), 'B');
  assert.equal(await pageA.locator('#user').inputValue(), 'preservar'); assert.equal(await pageB.locator('#user').inputValue(), 'preservar');
  console.log('PASS: PWA real offline, SW/cache, atribuição cruzada negada e foco/campos preservados.');
} finally { await stop(); }
