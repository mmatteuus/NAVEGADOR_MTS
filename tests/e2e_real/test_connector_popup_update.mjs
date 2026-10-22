/** E2E real: popup, sessões isoladas e atualização/reload da extensão. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { createInterface } from 'node:readline';
import { spawn } from 'node:child_process';
import { createTestHttpServer } from './fixture_http_server.mjs';
import { MCPAgentClient } from './mcp_agent_client.mjs';

async function waitBridge(url) {
  for (let i = 0; i < 300; i++) {
    try { if ((await (await fetch(`${url}/bridge-status`)).json()).connected) return; } catch (_) {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  const status = await fetch(`${url}/bridge-status`).then(response => response.text()).catch(error => String(error));
  throw new Error(`Bridge MCP não conectou; status final=${status}`);
}

async function waitForWorkerReload(context, previous, timeout = 30000) {
  const existing = context.serviceWorkers().find(worker => worker !== previous);
  if (existing) return existing;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { context.off('serviceworker', onWorker); reject(new Error('Service Worker não recarregou no prazo.')); }, timeout);
    const onWorker = worker => {
      if (worker === previous) return;
      clearTimeout(timer); context.off('serviceworker', onWorker); resolve(worker);
    };
    context.on('serviceworker', onWorker);
  });
}

async function savePopup(popup, ids) {
  await popup.reload();
  await popup.locator('#tab-access-list input').first().waitFor();
  for (const box of await popup.locator('#tab-access-list input').all()) {
    const checked = ids.includes(Number(await box.getAttribute('value')));
    if (await box.isChecked() !== checked) await box.setChecked(checked);
  }
  await popup.locator('#save-tab-grants').click();
  await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('salva'));
}

async function launchVersioned(wsPort, version) {
  const require = createRequire(import.meta.url);
  const globalPlaywright = process.env.APPDATA ? path.join(process.env.APPDATA, 'npm/node_modules/playwright') : 'playwright';
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE || globalPlaywright);
  const root = path.resolve('temp/e2e-real', `connector_${version}_${Date.now()}`);
  const extDir = path.join(root, 'extension');
  await mkdir(root, { recursive: true }); await cp(path.resolve('src/extension'), extDir, { recursive: true });
  const manifestPath = path.join(extDir, 'manifest.json');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8')); manifest.version = version;
  await writeFile(manifestPath, JSON.stringify(manifest, null, 2));
  const constantsPath = path.join(extDir, 'common/constants.js');
  const constants = await readFile(constantsPath, 'utf8');
  await writeFile(constantsPath, constants.replace(/DEFAULT_PORT = 3456/, `DEFAULT_PORT = ${wsPort}`)
    .replace(/PORT_CANDIDATES = \[[^\]]+\]/, `PORT_CANDIDATES = [${wsPort}]`));
  const context = await chromium.launchPersistentContext(path.join(root, 'profile'), {
    headless: false, executablePath: process.env.QA_CHROMIUM || undefined,
    ignoreDefaultArgs: ['--disable-extensions'],
    args: [ ...(process.env.QA_HEADLESS === '0' ? [] : ['--headless=new']), '--no-sandbox', `--disable-extensions-except=${extDir}`, `--load-extension=${extDir}`]
  });
  const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 30000 });
  const extensionId = worker.url().split('/')[2];
  return { context, worker, extDir, extensionId,
    close: async () => { await context.close(); await rm(root, { recursive: true, force: true }); } };
}

if (!process.env.QA_RUN_REAL_E2E) {
  console.log('SKIP: defina QA_RUN_REAL_E2E=1 para executar Chromium real.');
  process.exit(0);
}

const http = await createTestHttpServer().start();
const child = spawn(process.env.QA_PYTHON || 'python', ['tests/e2e_real/fixture_mcp_bridge.py'], {
  windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
  env: { ...process.env, QA_PAUSE_EXTENSION_HELLO: '1' }
});
const line = await new Promise((resolve, reject) => {
  child.once('error', reject); createInterface({ input: child.stdout }).once('line', resolve);
});
const info = JSON.parse(line);
const sourceManifest = JSON.parse(await readFile(path.resolve('src/extension/manifest.json'), 'utf8'));
const currentVersion = sourceManifest.version;
const agentA = new MCPAgentClient(info.mcpUrl, 'connector-a');
const agentB = new MCPAgentClient(info.mcpUrl, 'connector-b');
await agentA.initialize(); await agentB.initialize();
const ctx = await launchVersioned(info.wsPort, '2.2.0');
let currentWorker = ctx.worker;
ctx.context.on('serviceworker', worker => { currentWorker = worker; worker.on('console', message => console.error(`[worker:${message.type()}] ${message.text()}`)); });
ctx.worker.on('console', message => console.error(`[worker:${message.type()}] ${message.text()}`));
ctx.worker.on('close', () => console.error('[worker] fechado'));
assert.equal(await ctx.worker.evaluate(() => chrome.runtime.getManifest().version), '2.2.0');
const manifestPath = path.join(ctx.extDir, 'manifest.json');
const updated = JSON.parse(await readFile(manifestPath, 'utf8')); updated.version = currentVersion;
await writeFile(manifestPath, JSON.stringify(updated, null, 2));
const refreshedPromise = waitForWorkerReload(ctx.context, ctx.worker);
await fetch(`${info.mcpUrl}/release-hello`, { method: 'POST' });
console.log(`E2E bridge=${info.wsPort}; extensão descartável configurada para essa porta.`);
let popup, page;
try {
  currentWorker = await refreshedPromise;
  currentWorker.on('console', message => console.error(`[worker:${message.type()}] ${message.text()}`));
  assert.equal(await currentWorker.evaluate(() => chrome.runtime.getManifest().version), currentVersion);
  ctx.worker = currentWorker;
  popup = await ctx.context.newPage();
  await popup.goto(`chrome-extension://${ctx.extensionId}/popup/popup.html`);
  page = await ctx.context.newPage(); await page.goto(`${http.url}/`);
  await waitBridge(info.mcpUrl);
} catch (error) {
  const probe = await ctx.context.newPage().catch(() => null);
  if (probe) {
    try { await probe.goto(`chrome-extension://${ctx.extensionId}/popup/popup.html`); }
    catch (probeError) { console.error(`[reload-probe] ${probeError.message}`); }
    console.error(`[reload-probe] workers=${ctx.context.serviceWorkers().map(worker => worker.url()).join(',') || 'none'}`);
    await probe.close().catch(() => {});
  }
  await ctx.close(); await fetch(`${info.mcpUrl}/stop`, { method: 'POST' }).catch(() => {});
  child.kill(); await http.stop(); throw error;
}

try {
  const browserTabs = await currentWorker.evaluate(() => chrome.tabs.query({}));
  const tabId = browserTabs.find(tab => tab.url === `${http.url}/`).id;
  await savePopup(popup, [tabId]);
  assert.equal((await agentA.callTool('browser_get_text', { tabId })).isError, false);
  assert.equal((await agentA.callTool('browser_get_text')).isError, false);
  const denied = await agentB.callTool('browser_get_text', { tabId });
  assert.equal(denied.isError, true); assert.match(denied.error, /TAB_ACCESS_DENIED|TAB_NOT_ALLOWED/);
  await popup.locator('#clear-tab-grants').click();
  await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('limpa'));
  const revoked = await agentA.callTool('browser_get_text', { tabId });
  assert.equal(revoked.isError, true); assert.match(revoked.error, /TAB_NOT_ALLOWED|TAB_ACCESS_DENIED/);
  assert.equal(await currentWorker.evaluate(() => chrome.runtime.getManifest().version), currentVersion);
  console.log('PASS: popup grant, tabId explícito/implícito, isolamento, revogação e reload.');
} finally {
  await ctx.close(); await fetch(`${info.mcpUrl}/stop`, { method: 'POST' }).catch(() => {});
  child.kill(); await http.stop();
}
