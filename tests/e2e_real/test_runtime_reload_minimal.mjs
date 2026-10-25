import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE || path.join(process.env.APPDATA || '', 'npm/node_modules/playwright'));
const root = path.resolve('temp/e2e-real', `reload_min_${Date.now()}`);
await mkdir(root, { recursive: true });
await writeFile(path.join(root, 'manifest.json'), JSON.stringify({ manifest_version: 3, name: 'Reload Matrix', version: '1.0.0', permissions: ['storage'], background: { service_worker: 'worker.js' }, action: { default_popup: 'popup.html' } }));
await writeFile(path.join(root, 'worker.js'), 'chrome.storage.local.set({boot: Date.now()});');
await writeFile(path.join(root, 'popup.html'), '<html><script src="popup.js"></script>popup</html>');
await writeFile(path.join(root, 'popup.js'), 'chrome.storage.local.get("boot").then(v => document.title = String(v.boot));');
const headless = process.env.QA_HEADLESS !== '0';
const context = await chromium.launchPersistentContext(path.join(root, 'profile'), { headless: false, ignoreDefaultArgs: ['--disable-extensions'], args: [headless ? '--headless=new' : '', '--no-sandbox', `--disable-extensions-except=${root}`, `--load-extension=${root}`].filter(Boolean) });
try {
  const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 10000 });
  const id = worker.url().split('/')[2];
  const beforePage = await context.newPage(); await beforePage.goto(`chrome-extension://${id}/popup.html`);
  const before = await beforePage.title(); await beforePage.close();
  const settings = await context.newPage(); await settings.goto('chrome://extensions');
  const profile = await settings.evaluate(async () => {
    const get = () => new Promise(resolve => chrome.developerPrivate.getProfileConfiguration(resolve));
    const beforeConfig = await get();
    await new Promise(resolve => chrome.developerPrivate.updateProfileConfiguration({ inDeveloperMode: true }, resolve));
    return { before: beforeConfig, after: await get() };
  });
  await settings.close();
  console.log(`developerMode=${JSON.stringify(profile)}`);
  await worker.evaluate(() => chrome.runtime.reload());
  await new Promise(resolve => setTimeout(resolve, 1000));
  const page = await context.newPage();
  try {
    await page.goto(`chrome-extension://${id}/popup.html`);
    await page.waitForFunction(previous => document.title !== previous, before, { timeout: 5000 });
    console.log(`PASS: minimal runtime.reload updated worker state (${before} -> ${await page.title()})`);
  } catch (error) {
    const diagnostic = await context.newPage();
    let text = '';
    try {
      await diagnostic.goto('chrome://extensions');
      text = JSON.stringify(await diagnostic.evaluate(async (extensionId) => {
        const info = typeof chrome?.developerPrivate?.getExtensionsInfo === 'function'
          ? await new Promise(resolve => chrome.developerPrivate.getExtensionsInfo({ includeDisabled: true, includeTerminated: true }, resolve)) : null;
        const reloadResult = typeof chrome?.developerPrivate?.reload === 'function'
          ? await new Promise(resolve => chrome.developerPrivate.reload(extensionId, resolve)) : null;
        return { body: document.body?.innerText || '', hasDeveloperPrivate: typeof chrome?.developerPrivate,
          keys: Object.keys(chrome?.developerPrivate || {}), info, reloadResult };
      }, id));
    } catch (probeError) { text = `probe=${probeError.message}`; }
    console.log(JSON.stringify({ id, error: error.message, serviceWorkers: context.serviceWorkers().map(item => item.url()), extensions: text }));
    throw error;
  }
} finally { await context.close(); await rm(root, { recursive: true, force: true }); }
