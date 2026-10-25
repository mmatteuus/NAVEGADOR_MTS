import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const listeners = [];
let calls = 0;
const context = {
  console: { log() {} },
  window: { __BrowserMTS__: { interaction: { clickElement: async () => { calls += 1; return { ok: true }; } } } },
  chrome: { runtime: { id: 'test-extension', onMessage: {
    addListener(fn) { listeners.push(fn); },
    removeListener(fn) { const index = listeners.indexOf(fn); if (index >= 0) listeners.splice(index, 1); }
  } } }
};
context.window.window = context.window;
const source = await readFile('src/extension/content/content_bridge.js', 'utf8');
vm.runInNewContext(source, context);
vm.runInNewContext(source, context);
assert.equal(listeners.length, 1, 'reinjecao deve deixar apenas um listener ativo');
await listeners[0]({ action: 'browser_click', params: {} }, {}, () => {});
assert.equal(calls, 1, 'acao mutavel deve executar uma vez');
console.log('PASS: reinjecao do content bridge nao duplica listeners nem acoes.');
