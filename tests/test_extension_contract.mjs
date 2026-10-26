/** Regressões do contrato de avaliação e de erros do content script. */
import assert from 'node:assert/strict';

globalThis.window = globalThis;
let handlers = {};
globalThis.addEventListener = (type, fn) => { handlers[type] = fn; };
globalThis.removeEventListener = (type) => { delete handlers[type]; };
globalThis.dispatchEvent = (event) => { if (handlers[event.type]) handlers[event.type](event); };
globalThis.CustomEvent = class CustomEvent {
  constructor(type, options) {
    this.type = type;
    this.detail = options.detail;
  }
};
let createdElement = null;
globalThis.document = {
  title: 'Página local',
  head: {
    appendChild: (elem) => {
      createdElement = elem;
      eval(elem.textContent);
    }
  },
  createElement: (tag) => ({ textContent: '', remove: () => {} })
};
let receivedWorld = '';
globalThis.chrome = {
  tabs: { query: async () => [{ id: 11, url: 'https://example.com', active: true }] },
  scripting: {
    executeScript: async (options) => {
      receivedWorld = options.world;
      const injected = eval(`(${options.func.toString()})`);
      return [{ result: await injected(...options.args) }];
    }
  }
};

const { evaluatePageScript } = await import('../src/extension/background/page_script_executor.js');
const { requireContentSuccess } = await import('../src/extension/background/content_response.js');

const title = await evaluatePageScript(undefined, 'return document.title');
assert.deepEqual(title, { success: true, result: 'Página local', type: 'string' });
assert.equal(receivedWorld, 'MAIN');

await assert.rejects(
  () => evaluatePageScript(11, 'throw new Error("falha da página")'),
  /JavaScript da página falhou: falha da página/
);
assert.throws(
  () => requireContentSuccess({ success: false, error: 'Elemento ausente' }),
  /Elemento ausente/
);
assert.deepEqual(requireContentSuccess({ success: true, data: 1 }), { success: true, data: 1 });
console.log('[PASS] avaliação MAIN e erros internos do content script têm contrato explícito.');
