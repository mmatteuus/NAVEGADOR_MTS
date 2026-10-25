import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || path.join(process.env.APPDATA || '', 'npm/node_modules/playwright'));
const root = path.resolve('temp/e2e-real', `reload_matrix_${Date.now()}`);
const extDir = path.join(root, 'extension');
await mkdir(root, { recursive: true });
await cp(path.resolve('src/extension'), extDir, { recursive: true });
const context = await chromium.launchPersistentContext(path.join(root, 'profile'), {
  headless: false, executablePath: process.env.QA_CHROMIUM || undefined,
  dumpio: true, ignoreDefaultArgs: ['--disable-extensions'], args: ['--headless=new', '--no-sandbox', `--disable-extensions-except=${extDir}`, `--load-extension=${extDir}`]
});

const workers = () => context.serviceWorkers();
async function firstWorker() { return workers()[0] || context.waitForEvent('serviceworker', { timeout: 10000 }); }
async function reloadFrom(worker) {
  let closed = false;
  worker.on('close', () => { closed = true; });
  const next = new Promise(resolve => context.once('serviceworker', resolve));
  const id = worker.url().split('/')[2];
  await worker.evaluate(() => chrome.runtime.reload());
  const wake = await context.newPage().catch(() => null);
  if (wake) { await wake.goto(`chrome-extension://${id}/popup/popup.html`).catch(() => {}); }
  await Promise.race([next, new Promise(resolve => setTimeout(resolve, 3000))]);
  await wake?.close().catch(() => {});
  const candidate = workers()[0];
  if (!candidate) throw new Error(`runtime.reload removed worker (closed=${closed})`);
  return candidate;
}
async function extensionDiagnostics() {
  const page = await context.newPage();
  try {
    await page.goto('chrome://extensions', { waitUntil: 'domcontentloaded', timeout: 5000 });
    const items = await page.locator('extensions-item').evaluateAll(elements => elements.map(element => ({
      id: element.id, data: element.data || null
    })));
    return { items, text: (await page.locator('body').innerText()).slice(0, 3000) };
  } catch (error) { return { items: [], text: `probe-error=${error.message}` }; }
  finally { await page.close().catch(() => {}); }
}

try {
  let worker = await firstWorker();
  const id = worker.url().split('/')[2];
  const initial = await worker.evaluate(() => chrome.runtime.getManifest().version);
  worker = await reloadFrom(worker);
  assert.equal(await worker.evaluate(() => chrome.runtime.getManifest().version), initial);
  const constantsPath = path.join(extDir, 'common/constants.js');
  await writeFile(constantsPath, `${await readFile(constantsPath, 'utf8')}\n// reload-matrix-marker\n`);
  worker = await reloadFrom(worker);
  assert.equal(await worker.evaluate(() => chrome.runtime.getManifest().version), initial);
  const manifestPath = path.join(extDir, 'manifest.json');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  manifest.version = '2.3.9';
  await writeFile(manifestPath, JSON.stringify(manifest, null, 2));
  await new Promise(resolve => setTimeout(resolve, 1000));
  const diagnostics = await extensionDiagnostics();
  console.log(JSON.stringify({ id, initial, workersAfterManifest: workers().map(item => item.url()), diagnostics }, null, 2));
} finally {
  await context.close().catch(() => {});
  await rm(root, { recursive: true, force: true });
}
