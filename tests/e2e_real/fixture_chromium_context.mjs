/**
 * @file fixture_chromium_context.mjs
 * @description Instancia perfis isolados do Chromium real com ou sem extensão MV3
 * utilizando Playwright em modo headless moderno (--headless=new).
 */
import { createRequire } from 'node:module';
import { cp, readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);
const fs = require('node:fs');
const globalPlaywright = process.env.APPDATA ? path.join(process.env.APPDATA, 'npm/node_modules/playwright') : null;
const playwrightPath = process.env.PLAYWRIGHT_MODULE ||
  (globalPlaywright && fs.existsSync(globalPlaywright) ? globalPlaywright : 'playwright');
const { chromium } = require(playwrightPath);

export async function launchAgentContext({ sessionId, wsPort = null, loadExtension = false }) {
  await mkdir(path.resolve('temp/e2e-real'), { recursive: true });
  const profileDir = path.resolve('temp/e2e-real', `profile_${sessionId}_${Date.now()}`);
  let extDir = null;
  const args = ['--headless=new', '--no-sandbox'];

  if (loadExtension) {
    if (!wsPort) throw new Error('wsPort é obrigatório para carregar a extensão.');
    extDir = path.resolve('temp/e2e-real', `ext_${sessionId}_${Date.now()}`);
    await cp(path.resolve('src/extension'), extDir, { recursive: true });

    const constFile = path.join(extDir, 'common/constants.js');
    const source = await readFile(constFile, 'utf8');
    const modified = source
      .replace(/DEFAULT_PORT = 3456/, `DEFAULT_PORT = ${wsPort}`)
      .replace(/PORT_CANDIDATES = \[[^\]]+\]/, `PORT_CANDIDATES = [${wsPort}]`);
    await writeFile(constFile, modified);

    args.push(`--disable-extensions-except=${extDir}`, `--load-extension=${extDir}`);
  }

  const context = await chromium.launchPersistentContext(profileDir, {
    headless: false,
    executablePath: process.env.QA_CHROMIUM || undefined,
    args
  });

  let worker = null;
  let extensionId = null;

  if (loadExtension) {
    worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 30000 });
    extensionId = worker.url().split('/')[2];
  }

  const close = async () => {
    try {
      await context.close();
    } catch (_) {}
    await new Promise(res => setTimeout(res, 500));
    for (const d of [profileDir, extDir].filter(Boolean)) {
      try {
        await rm(d, { recursive: true, force: true });
      } catch (_) {}
    }
  };

  return { context, worker, extensionId, profileDir, close };
}
