/** Testes de segurança e isolamento do eval_runner.js no navegador. */
import assert from 'node:assert/strict';

class MockElement {
  constructor(tagName, id = '', className = '', textContent = '') {
    this.tagName = tagName;
    this.id = id;
    this.className = className;
    this.textContent = textContent;
  }
}

globalThis.window = globalThis;
globalThis.Element = MockElement;
globalThis.__BrowserMTS__ = { secretToken: 'SENSITIVE_KEY_12345' };
globalThis.chrome = { runtime: { id: 'ext-test-id' } };
globalThis.browser = { runtime: { id: 'ext-test-id' } };
globalThis.document = { title: 'Página de Teste' };

await import('../src/extension/content/eval_runner.js');
const { evaluateScript } = globalThis.__BrowserMTS__.evalRunner;

// 1. Execução legítima e assíncrona
let res = await evaluateScript('return 10 + 20;');
assert.equal(res.success, true);
assert.equal(res.result, 30);

res = await evaluateScript('const val = await Promise.resolve(42); return val;');
assert.equal(res.success, true);
assert.equal(res.result, 42);

// 2. Bloqueio de identificadores diretos
res = await evaluateScript('return typeof __BrowserMTS__;');
assert.equal(res.success, true);
assert.equal(res.result, 'undefined');

res = await evaluateScript('return typeof chrome;');
assert.equal(res.success, true);
assert.equal(res.result, 'undefined');

// 3. Bloqueio de propriedades em aliases globais
for (const globalAlias of ['window', 'globalThis', 'self', 'top', 'parent']) {
  res = await evaluateScript(`return ${globalAlias}.__BrowserMTS__;`);
  assert.equal(res.success, true);
  assert.equal(res.result, undefined);
}

// 4. Bloqueio de mutação e redefinição
res = await evaluateScript('window.__BrowserMTS__ = "tampered";');
assert.equal(res.success, false);
assert.match(res.error, /Acesso negado à propriedade restrita/);

// 5. Tentativa de fuga via Function, eval e protótipos de construtores
res = await evaluateScript('const f = Function("return this"); const ctx = await f(); return ctx.__BrowserMTS__;');
assert.equal(res.success, true);
assert.equal(res.result, undefined);

res = await evaluateScript('return await eval("window.__BrowserMTS__");');
assert.equal(res.success, true);
assert.equal(res.result, undefined);

res = await evaluateScript('return ({}).constructor.constructor("return __BrowserMTS__")();');
assert.equal(res.success, true);
assert.equal(res.result, undefined);

res = await evaluateScript('return (async () => {}).constructor("return __BrowserMTS__")();');
assert.equal(res.success, true);
assert.equal(res.result, undefined);

res = await evaluateScript('return (function* () {}).constructor("return __BrowserMTS__")();');
assert.equal(res.success, true);
assert.equal(res.result, undefined);

// 6. Serialização de Elementos DOM e Funções
const el = new MockElement('BUTTON', 'btn1', 'btn-primary', 'Clique aqui');
globalThis.document.querySelector = () => el;
res = await evaluateScript('return document.querySelector("button");');
assert.equal(res.success, true);
assert.deepEqual(res.result, { tagName: 'button', id: 'btn1', className: 'btn-primary', text: 'Clique aqui' });

// 7. Validação de entradas vazias ou inválidas
await assert.rejects(evaluateScript(''), /Nenhum código JavaScript fornecido/);

console.log('[PASS] eval_runner sandbox passou em todos os testes de segurança e isolamento.');
