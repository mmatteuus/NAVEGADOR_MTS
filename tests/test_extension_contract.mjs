/** Regressões do contrato de avaliação e de erros do content script. */
import assert from 'node:assert/strict';

const eventListeners = new Map();
globalThis.window = {
  addEventListener: (type, fn) => eventListeners.set(type, fn),
  removeEventListener: (type) => eventListeners.delete(type),
  dispatchEvent: (evt) => {
    const fn = eventListeners.get(evt.type);
    if (fn) fn(evt);
  }
};
globalThis.CustomEvent = class CustomEvent {
  constructor(type, params) {
    this.type = type;
    this.detail = params?.detail;
  }
};
globalThis.document = {
  title: 'Página local',
  createElement: () => {
    const el = {
      remove: () => {},
      set textContent(code) {
        // Simula execução síncrona de tag <script> ao anexar
        try {
          const fn = Function(`return (async () => { ${code} })()`);
          fn();
        } catch (e) {}
      }
    };
    return el;
  },
  head: {
    appendChild: (el) => {}
  }
};

let receivedWorld = '';
globalThis.chrome = {
  tabs: { query: async () => [{ id: 11, url: 'https://example.com', active: true }] },
  scripting: {
    executeScript: async (options) => {
      receivedWorld = options.world;
      const funcStr = options.func.toString();
      const injected = Function(`return (${funcStr})`)();
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
