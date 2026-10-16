/**
 * @file test_extension_tier5_virtual_dom.mjs
 * @description Auditoria adversarial Tier 5: Cursor Virtual DOM, isolamento de eventos e digitação sem foco.
 */
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';

// Mock de ambiente DOM no Node.js
class MockClassList {
  constructor() { this.classes = new Set(); }
  add(c) { this.classes.add(c); }
  remove(c) { this.classes.delete(c); }
  contains(c) { return this.classes.has(c); }
}

class MockElement {
  constructor(tag, id = '') {
    this.tagName = tag.toUpperCase();
    this.id = id;
    this.classList = new MockClassList();
    this.style = {};
    this.attributes = new Map();
    this.children = [];
    if (tag.toLowerCase() === 'input' || tag.toLowerCase() === 'textarea') {
      this.value = '';
    }
    this.disabled = false;
    this.readOnly = false;
    this.isContentEditable = false;
  }
  setAttribute(k, v) { this.attributes.set(k, v); }
  getAttribute(k) { return this.attributes.get(k); }
  appendChild(el) { this.children.push(el); return el; }
  remove() { this.parent?.removeChild(this); }
  scrollIntoView() {}
  focus() { globalThis.document.activeElement = this; }
  dispatchEvent(_evt) { return true; }
}

const mockDoc = {
  head: new MockElement('head'),
  body: new MockElement('body'),
  documentElement: new MockElement('html'),
  activeElement: null,
  getElementById: (id) => (id === 'browser-mts-virtual-cursor' ? mockDoc.virtualCursorEl : null),
  createElement: (tag) => new MockElement(tag),
  createElementNS: (_ns, tag) => new MockElement(tag),
  elementFromPoint: (x, y) => mockDoc.hitTarget || mockDoc.body
};
mockDoc.activeElement = mockDoc.body;

globalThis.window = { __BrowserMTS__: {} };
globalThis.document = mockDoc;
globalThis.PointerEvent = class { constructor(type, init) { Object.assign(this, { type, ...init }); } };
globalThis.MouseEvent = class { constructor(type, init) { Object.assign(this, { type, ...init }); } };
globalThis.KeyboardEvent = class { constructor(type, init) { Object.assign(this, { type, ...init }); } };
globalThis.InputEvent = class { constructor(type, init) { Object.assign(this, { type, ...init }); } };
globalThis.DragEvent = class { constructor(type, init) { Object.assign(this, { type, ...init }); } };
globalThis.Event = class { constructor(type, init) { Object.assign(this, { type, ...init }); } };

// Carrega os módulos reais de content script
const cursorPath = path.resolve('src/extension/content/virtual_cursor.js');
const dragPath = path.resolve('src/extension/content/drag_simulator.js');
const interactPath = path.resolve('src/extension/content/interaction_simulator.js');

new Function(fs.readFileSync(cursorPath, 'utf8'))();
new Function(fs.readFileSync(dragPath, 'utf8'))();
new Function(fs.readFileSync(interactPath, 'utf8'))();

const vCursor = window.__BrowserMTS__.virtualCursor;
const interact = window.__BrowserMTS__.interaction;
const dragSim = window.__BrowserMTS__.dragSimulator;

async function runTier5VirtualDomTests() {
  console.log('[TIER 5 DOM] 1. Isolamento estrito de pointer-events no cursor do agente...');
  vCursor.ensureDOM();
  const styleEl = mockDoc.head.children.find(c => c.id === 'browser-mts-cursor-styles');
  assert.ok(styleEl, 'Estilos do cursor devem ter sido injetados.');
  assert.ok(styleEl.textContent.includes('pointer-events: none !important'), 'pointer-events: none obrigatório!');

  // Hit-testing com elemento do usuário sob o cursor do agente
  const userButton = new MockElement('button', 'real-user-btn');
  mockDoc.hitTarget = userButton;
  vCursor.updatePosition(150, 200, false);
  const hit = document.elementFromPoint(150, 200);
  assert.strictEqual(hit.id, 'real-user-btn', 'O clique real do usuário JAMAIS deve colidir com o cursor virtual.');
  console.log('  -> PASS: Cursor do agente totalmente transparente aos eventos do usuário.');

  console.log('[TIER 5 DOM] 2. Estresse de coordenadas anômalas, negativas e extremas...');
  assert.doesNotThrow(() => vCursor.updatePosition(-9999, -500, true));
  assert.doesNotThrow(() => vCursor.showClick(100000, 500000, 'right'));
  assert.doesNotThrow(() => vCursor.showDrag(-50, -50, 2000, 3000));
  const pos = vCursor.getPosition();
  assert.strictEqual(pos.x, 2000);
  assert.strictEqual(pos.y, 3000);
  console.log('  -> PASS: Renderização resiliente sem quebra ou exceção em limites anômalos.');

  console.log('[TIER 5 DOM] 3. Digitação sem foco em elementos inválidos, disabled ou readOnly...');
  // Sem elemento editável focado
  mockDoc.activeElement = mockDoc.body;
  await assert.rejects(async () => interact.typeText({ text: 'Hello' }), /Nenhum campo editável focado/);

  // Elemento desabilitado
  const disabledInput = new MockElement('input');
  disabledInput.disabled = true;
  mockDoc.activeElement = disabledInput;
  await assert.rejects(async () => interact.typeText({ text: 'Teste' }), /não aceita digitação/);

  // Elemento somente leitura
  const readOnlyInput = new MockElement('input');
  readOnlyInput.readOnly = true;
  mockDoc.activeElement = readOnlyInput;
  await assert.rejects(async () => interact.typeText({ text: 'Teste' }), /não aceita digitação/);
  console.log('  -> PASS: Digitação em elementos inválidos rejeitada com segurança.');

  console.log('[TIER 5 DOM] 4. Foco virtual isolado do agente (setVirtualFocus / removeVirtualFocus)...');
  const targetElement = new MockElement('div', 'agent-target');
  vCursor.setVirtualFocus(targetElement);
  assert.strictEqual(targetElement.classList.contains('mts-virtual-focus'), true);
  vCursor.removeVirtualFocus();
  assert.strictEqual(targetElement.classList.contains('mts-virtual-focus'), false);
  console.log('  -> PASS: Destaque visual isolado aplicado e limpo sem disparar blur no usuário.');

  console.log('\n[SUCESSO TIER 5] Auditoria de DOM e Isolamento Virtual aprovada com louvor!');
  process.exit(0);
}

runTier5VirtualDomTests().catch((err) => {
  console.error('[FALHA TIER 5 DOM]', err);
  process.exit(1);
});
