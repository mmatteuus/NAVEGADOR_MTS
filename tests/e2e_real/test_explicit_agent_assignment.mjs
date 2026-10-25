/** E2E real opt-in: atribuição explícita, isolamento e foco do usuário. */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { createTestHttpServer } from './fixture_http_server.mjs';
import { launchAgentContext } from './fixture_chromium_context.mjs';
import { MCPAgentClient } from './mcp_agent_client.mjs';

if (process.env.RUN_EXPLICIT_ASSIGNMENT_E2E !== '1') {
  console.log('SKIP: defina RUN_EXPLICIT_ASSIGNMENT_E2E=1 para Chromium real.'); process.exit(0);
}
const http = await createTestHttpServer().start();
const log = message => console.log(`[assignment-e2e] ${message}`);
const child = spawn(process.env.QA_PYTHON || 'python', ['tests/e2e_real/fixture_mcp_bridge.py'], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
child.stderr.on('data', data => console.error(`[bridge] ${data}`));
const info = JSON.parse(await Promise.race([
  new Promise(resolve => createInterface({ input: child.stdout }).once('line', resolve)),
  new Promise((_, reject) => setTimeout(() => reject(new Error('fixture startup timeout')), 15000))
]));
log(`bridge ready ${info.mcpUrl}`);
const a = new MCPAgentClient(info.mcpUrl, 'agent-a'), b = new MCPAgentClient(info.mcpUrl, 'agent-b');
await a.initialize(); await b.initialize();
log('agents initialized');
const ctx = await launchAgentContext({ sessionId: 'connector', wsPort: info.wsPort, loadExtension: true });
log('extension context ready');
const stop = async () => { await ctx.close(); await fetch(`${info.mcpUrl}/stop`, { method: 'POST' }).catch(() => {}); child.kill(); await http.stop(); };
try {
  for (let i = 0; i < 100; i++) { try { if ((await (await fetch(`${info.mcpUrl}/bridge-status`)).json()).connected) break; } catch (_) {} await new Promise(r => setTimeout(r, 100)); }
  const pageA = await ctx.context.newPage(), pageB = await ctx.context.newPage();
  await pageA.goto(`${http.url}/agent-a/set-auth`); await pageB.goto(`${http.url}/agent-b/check-auth`);
  await pageA.evaluate(() => { document.body.innerHTML = '<input id="user" value="preservar-A"><input id="agent" value="">'; });
  await pageB.evaluate(() => { document.body.innerHTML = '<input id="user" value="preservar-B"><input id="agent" value="">'; });
  const popup = await ctx.context.newPage(); await popup.goto(`chrome-extension://${ctx.extensionId}/popup/popup.html`);
  log('popup opened');
  await popup.locator('#tab-access-list input').first().waitFor({ timeout: 15000 });
  const tabs = await ctx.worker.evaluate(() => chrome.tabs.query({}));
  const tabA = tabs.find(t => t.url === `${http.url}/agent-a/set-auth`).id;
  const tabB = tabs.find(t => t.url === `${http.url}/agent-b/check-auth`).id;
  for (const [tabId, sid] of [[tabA, 'agent-a'], [tabB, 'agent-b']]) {
    const box = popup.locator(`#tab-access-list input[value="${tabId}"]`); await box.check();
    await popup.locator(`select[data-tab-id="${tabId}"]`).selectOption(sid);
  }
  await popup.locator('#save-tab-grants').click();
  log('assignments saved');
  await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('salva'));
  assert.equal((await a.callTool('browser_get_text', { tabId: tabA })).isError, false);
  assert.equal((await b.callTool('browser_get_text', { tabId: tabB })).isError, false);
  const denied = await b.callTool('browser_get_text', { tabId: tabA });
  assert.equal(denied.isError, true); assert.match(denied.error, /TAB_ACCESS_DENIED|TAB_NOT_ALLOWED/);
  await pageA.locator('#user').focus(); await pageB.locator('#user').focus();
  const focusBefore = await Promise.all([pageA, pageB].map(page => page.evaluate(() => ({
    activeId: document.activeElement?.id, selectionStart: document.activeElement?.selectionStart,
    selectionEnd: document.activeElement?.selectionEnd
  }))));
  const activeBefore = await ctx.worker.evaluate(() => chrome.tabs.query({}).then(tabs =>
    tabs.filter(tab => tab.id).map(tab => [tab.id, !!tab.active])));
  const replies = await Promise.all([
    a.callTool('browser_type', { tabId: tabA, selector: '#agent', text: 'A' }),
    b.callTool('browser_type', { tabId: tabB, selector: '#agent', text: 'B' })
  ]);
  assert.ok(replies.every(reply => reply.isError === false), JSON.stringify(replies));
  assert.equal(await pageA.locator('#agent').inputValue(), 'A');
  assert.equal(await pageB.locator('#agent').inputValue(), 'B');
  assert.equal(await pageA.locator('#user').inputValue(), 'preservar-A');
  assert.equal(await pageB.locator('#user').inputValue(), 'preservar-B');
  assert.deepEqual(await Promise.all([pageA, pageB].map(page => page.evaluate(() => ({
    activeId: document.activeElement?.id, selectionStart: document.activeElement?.selectionStart,
    selectionEnd: document.activeElement?.selectionEnd
  })))), focusBefore);
  assert.deepEqual(await ctx.worker.evaluate(() => chrome.tabs.query({}).then(tabs =>
    tabs.filter(tab => tab.id).map(tab => [tab.id, !!tab.active]))), activeBefore);
  await popup.locator(`select[data-tab-id="${tabA}"]`).selectOption('agent-b'); await popup.locator('#save-tab-grants').click();
  await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('salva'));
  assert.equal((await b.callTool('browser_get_text', { tabId: tabA })).isError, false);
  assert.equal((await a.callTool('browser_get_text', { tabId: tabA })).isError, true);
  await popup.locator(`#tab-access-list input[value="${tabB}"]`).uncheck(); await popup.locator('#save-tab-grants').click();
  await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('salva'));
  assert.equal((await b.callTool('browser_get_text', { tabId: tabB })).isError, true);
  await popup.locator('#clear-tab-grants').click();
  const revoked = await b.callTool('browser_get_text', { tabId: tabA });
  assert.equal(revoked.isError, true); assert.match(revoked.error, /TAB_ACCESS_DENIED|TAB_NOT_ALLOWED/);
  console.log('PASS: atribuição concorrente, bloqueio cruzado, reassociação, revogação e foco preservado.');
} finally { await stop(); }
