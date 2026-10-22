/** Fixture real Chromium + extensão + roteador MCP, isolada da instalação pessoal. */
import { createRequire } from 'node:module';
import { cp, mkdtemp, readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import assert from 'node:assert/strict';

export async function setup() {
  const require = createRequire(import.meta.url);
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
  await mkdir('temp', { recursive: true });
  const folder = await mkdtemp(path.resolve('temp/keyboard-e2e-'));
  const child = spawn(process.env.QA_PYTHON || 'python', ['tests/keyboard_e2e_bridge.py'], {
    windowsHide: true, stdio: ['ignore', 'pipe', 'pipe']
  });
  child.stderr.on('data', data => process.stderr.write(data));
  const line = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Ponte de QA não iniciou')), 15000);
    child.once('error', reject);
    createInterface({ input: child.stdout }).once('line', text => { clearTimeout(timer); resolve(text); });
  });
  const { url, wsPort } = JSON.parse(line);
  const extension = path.join(folder, 'extension');
  await cp(path.resolve('src/extension'), extension, { recursive: true });
  const constants = path.join(extension, 'common/constants.js');
  const source = await readFile(constants, 'utf8');
  // Só a cópia descartável recebe a porta dinâmica; código de produto não é alterado.
  await writeFile(constants, source.replace(/DEFAULT_PORT = 3456/, `DEFAULT_PORT = ${wsPort}`)
    .replace(/PORT_CANDIDATES = \[[^\]]+\]/, `PORT_CANDIDATES = [${wsPort}]`));
  const launch = () => chromium.launchPersistentContext(path.join(folder, 'profile'), {
    channel: 'chromium', headless: true,
    executablePath: process.env.QA_CHROMIUM || undefined,
    args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`]
  });
  let context = await launch();
  const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
  const extensionId = worker.url().split('/')[2];
  const call = async (name, args = {}, expectedError) => {
    const response = await fetch(`${url}/command`, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, args }) });
    const result = await response.json();
    if (expectedError) {
      assert.equal(result.isError, true); assert.match(result.content[0].text, expectedError); return result;
    }
    assert.equal(result.isError, false, JSON.stringify(result));
    return JSON.parse(result.content.find(item => item.type === 'text').text);
  };
  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${extensionId}/popup/popup.html`);
  const page = await context.newPage();
  await page.goto(url);
  for (let i = 0; i < 100; i++) {
    if ((await (await fetch(`${url}/status`)).json()).connected) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.equal((await (await fetch(`${url}/status`)).json()).connected, true);
  const tabs = await call('browser_manage_tabs', { action: 'list', currentWindowOnly: false });
  const tabId = tabs.find(tab => tab.url === `${url}/`).id;
  const save = async ids => {
    await popup.reload();
    await popup.locator('#tab-access-list input').first().waitFor();
    for (const checkbox of await popup.locator('#tab-access-list input').all()) {
      await checkbox.setChecked(ids.includes(Number(await checkbox.getAttribute('value'))));
    }
    await popup.locator('#save-tab-grants').click();
    await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('salva'));
    assert.deepEqual(await popup.locator('#tab-access-list input:checked').evaluateAll(
      inputs => inputs.map(input => Number(input.value)).sort((a, b) => a - b)), [...ids].sort((a, b) => a - b));
    assert.ok((await popup.locator('#tab-access-list').textContent()).includes('Teclado QA'));
  };
  const restart = async () => {
    await context.close();
    context = await launch();
    return context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
  };
  const close = async () => { await context.close(); await fetch(`${url}/stop`, { method: 'POST' }); };
  return { context, worker, page, popup, call, save, tabId, url, close, folder, restart };
}
