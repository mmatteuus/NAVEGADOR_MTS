/**
 * @file eval_runner.js
 * @description Executor isolado e sandboxed de scripts customizados na página web.
 */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  const BLOCKED_KEYS = new Set(['__BrowserMTS__', 'chrome', 'browser']);

  function createSandboxedFunction(sandboxProxy, shadowNames, shadowValues) {
    return function SandboxedFunction(...args) {
      const body = args.pop() || '';
      const paramNames = args;
      const fn = new Function(...shadowNames, ...paramNames, `return (async () => { ${body} })();`);
      return function (...callArgs) {
        return fn.call(sandboxProxy, ...shadowValues, ...callArgs);
      };
    };
  }

  function createSandboxEnvironment(targetWindow) {
    let sandboxedFn;
    const proxy = new Proxy(targetWindow, {
      get(target, prop, receiver) {
        if (BLOCKED_KEYS.has(prop)) return undefined;
        if (['window', 'globalThis', 'self', 'top', 'parent'].includes(prop)) return proxy;
        if (prop === 'Function') return sandboxedFn;
        if (prop === 'eval') {
          return function (code) { return sandboxedFn(`return ${code}`)(); };
        }
        const val = Reflect.get(target, prop, receiver);
        return typeof val === 'function' ? val.bind(target) : val;
      },
      set(target, prop, value, receiver) {
        if (BLOCKED_KEYS.has(prop)) throw new Error(`Acesso negado à propriedade restrita: ${String(prop)}`);
        return Reflect.set(target, prop, value, receiver);
      },
      defineProperty(target, prop, descriptor) {
        if (BLOCKED_KEYS.has(prop)) throw new Error(`Acesso negado à propriedade restrita: ${String(prop)}`);
        return Reflect.defineProperty(target, prop, descriptor);
      },
      deleteProperty(target, prop) {
        if (BLOCKED_KEYS.has(prop)) throw new Error(`Acesso negado à propriedade restrita: ${String(prop)}`);
        return Reflect.deleteProperty(target, prop);
      },
      has(target, prop) {
        if (BLOCKED_KEYS.has(prop)) return false;
        return Reflect.has(target, prop);
      }
    });

    const shadowNames = ['window', 'globalThis', 'self', 'top', 'parent', '__BrowserMTS__', 'chrome', 'browser'];
    const shadowValues = [proxy, proxy, proxy, proxy, proxy, undefined, undefined, undefined];
    sandboxedFn = createSandboxedFunction(proxy, shadowNames, shadowValues);

    return { proxy, shadowNames, shadowValues, sandboxedFn };
  }

  async function withProtectedConstructors(sandboxedFn, callback) {
    const AsyncProto = Object.getPrototypeOf(async function () {});
    const GeneratorProto = Object.getPrototypeOf(function* () {});
    const targets = [
      { obj: Object.prototype, desc: Object.getOwnPropertyDescriptor(Object.prototype, 'constructor') },
      { obj: Function.prototype, desc: Object.getOwnPropertyDescriptor(Function.prototype, 'constructor') },
      { obj: AsyncProto, desc: Object.getOwnPropertyDescriptor(AsyncProto, 'constructor') },
      { obj: GeneratorProto, desc: Object.getOwnPropertyDescriptor(GeneratorProto, 'constructor') }
    ];
    try {
      for (const t of targets) {
        if (t.obj) Object.defineProperty(t.obj, 'constructor', { get() { return sandboxedFn; }, configurable: true });
      }
      return await callback();
    } finally {
      for (const t of targets) {
        if (t.obj && t.desc) Object.defineProperty(t.obj, 'constructor', t.desc);
      }
    }
  }

  /**
   * Executa script JavaScript no contexto seguro da página e aguarda Promises.
   * @param {string} script - Código JavaScript a ser executado.
   * @returns {Promise<object>} Resultado serializado ou detalhes do erro.
   */
  async function evaluateScript(script) {
    if (typeof script !== 'string' || !script.trim()) {
      throw new Error('Nenhum código JavaScript fornecido para avaliação.');
    }

    try {
      const win = typeof window !== 'undefined' ? window : globalThis;
      const { proxy: sandbox, shadowNames, shadowValues, sandboxedFn } = createSandboxEnvironment(win);
      const allNames = [...shadowNames, 'Function', 'eval'];
      const evalFn = function (code) { return sandboxedFn(`return ${code}`)(); };
      const allValues = [...shadowValues, sandboxedFn, evalFn];

      const executionResult = await withProtectedConstructors(sandboxedFn, async () => {
        const evaluatorFn = new Function(...allNames, `return (async () => { ${script} })();`);
        return evaluatorFn.call(sandbox, ...allValues);
      });

      let serializableResult = executionResult;
      if (typeof executionResult === 'function') {
        serializableResult = executionResult.toString();
      } else if (typeof Element !== 'undefined' && executionResult instanceof Element) {
        serializableResult = {
          tagName: executionResult.tagName.toLowerCase(),
          id: executionResult.id || null,
          className: executionResult.className || null,
          text: executionResult.textContent?.trim().slice(0, 100) || ''
        };
      }

      return { success: true, result: serializableResult, type: typeof executionResult };
    } catch (err) {
      return { success: false, error: err.message || String(err), stack: err.stack || null };
    }
  }

  window.__BrowserMTS__.evalRunner = { evaluateScript };
})();
