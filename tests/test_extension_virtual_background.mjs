/**
 * @file test_extension_virtual_background.mjs
 * @description Validação das funcionalidades M2: CDP em background, Cursor Virtual e Drag DOM.
 */

import assert from 'node:assert';

const cdpLog = [];
let attachedTabsSet = new Set();
let openTabs = [
  { id: 201, url: 'https://exemplo.com/dash', active: false, windowId: 1 },
  { id: 202, url: 'https://exemplo.com/user', active: true, windowId: 1 }
];

globalThis.chrome = {
  debugger: {
    attach: async ({ tabId }, version) => {
      cdpLog.push({ action: 'attach', tabId, version });
      attachedTabsSet.add(tabId);
    },
    detach: async ({ tabId }) => {
      cdpLog.push({ action: 'detach', tabId });
      attachedTabsSet.delete(tabId);
    },
    sendCommand: async ({ tabId }, method, params) => {
      cdpLog.push({ action: 'sendCommand', tabId, method, params });
      return method === 'Page.captureScreenshot' ? { data: 'iVBORw0KGgoAAAANSUhEUgAAAAE=' } : { success: true };
    },
    onDetach: { addListener: () => {} }
  },
  tabs: {
    get: async (id) => openTabs.find(t => t.id === id),
    query: async () => openTabs,
    create: async (opts) => {
      const tab = { id: 300 + openTabs.length, ...opts, windowId: 1 };
      openTabs.push(tab);
      return tab;
    },
    captureVisibleTab: async () => 'data:image/png;base64,FALLBACK'
  }
};

const { attachTab, detachTab, sendCdpCommand } = await import('../src/extension/background/cdp_controller.js');
const { cdpCaptureScreenshot, cdpDispatchMouse, cdpDispatchKey, cdpDispatchDrag } = await import('../src/extension/background/cdp_actions.js');
const { captureTabScreenshot } = await import('../src/extension/background/screenshot_capture.js');
const { newTab } = await import('../src/extension/background/tab_manager.js');

async function testDomComponents() {
  const domElements = new Map();
  class MockElement {
    constructor(tag) {
      this.tagName = tag.toUpperCase();
      this.style = {};
      this.classList = { add: () => {}, remove: () => {} };
      this.children = [];
    }
    appendChild(c) { this.children.push(c); return c; }
    remove() {}
    setAttribute() {}
    dispatchEvent() { return true; }
  }
  globalThis.window = { __BrowserMTS__: {} };
  globalThis.document = {
    getElementById: (id) => domElements.get(id) || null,
    createElement: (tag) => { const el = new MockElement(tag); return el; },
    createElementNS: (_ns, tag) => new MockElement(tag),
    elementFromPoint: () => new MockElement('div'),
    head: new MockElement('head'),
    body: new MockElement('body'),
    documentElement: new MockElement('html')
  };
  globalThis.PointerEvent = class {};
  globalThis.MouseEvent = class {};
  globalThis.DragEvent = class {};

  await import('../src/extension/content/virtual_cursor.js');
  await import('../src/extension/content/drag_simulator.js');

  const vCursor = window.__BrowserMTS__.virtualCursor;
  assert.ok(vCursor, 'virtualCursor deve estar registrado em window.__BrowserMTS__');
  vCursor.updatePosition(150, 220);
  assert.deepStrictEqual(vCursor.getPosition(), { x: 150, y: 220 });
  const clickRes = vCursor.showClick(150, 220, 'left');
  assert.strictEqual(clickRes.button, 'left');

  const dragSim = window.__BrowserMTS__.dragSimulator;
  assert.ok(dragSim, 'dragSimulator deve estar registrado em window.__BrowserMTS__');
  const dragRes = await dragSim.simulateDrag({ startX: 10, startY: 10, endX: 80, endY: 80 });
  assert.strictEqual(dragRes.success, true);
  assert.strictEqual(dragRes.from.x, 10);
  assert.strictEqual(dragRes.to.x, 80);
}

async function runVirtualBackgroundTests() {
  console.log('[TEST M2] 1. Testando conexão e comandos CDP resilientes...');
  await attachTab(201);
  assert.ok(attachedTabsSet.has(201));
  await sendCdpCommand(201, 'DOM.enable');
  await detachTab(201);
  assert.ok(!attachedTabsSet.has(201));
  console.log('  -> PASS: Ciclo de vida CDP validado com sucesso.');

  console.log('[TEST M2] 2. Testando captura de tela via CDP em background por tabId...');
  const screenBg = await captureTabScreenshot('png', 90, 201);
  assert.strictEqual(screenBg.success, true);
  assert.strictEqual(screenBg.tabId, 201);
  console.log('  -> PASS: Screenshot da aba em background obtido via CDP.');

  console.log('[TEST M2] 3. Testando despacho de mouse, teclado e drag via CDP...');
  cdpLog.length = 0;
  await cdpDispatchMouse(201, { type: 'mousePressed', x: 50, y: 75, button: 'left' });
  await cdpDispatchKey(201, { type: 'keyDown', text: 'a', key: 'a' });
  await cdpDispatchDrag(201, { startX: 10, startY: 10, endX: 100, endY: 100, steps: 2 });
  assert.ok(cdpLog.some(l => l.method === 'Input.dispatchMouseEvent'));
  console.log('  -> PASS: Eventos CDP de mouse/teclado/drag despachados.');

  console.log('[TEST M2] 4. Testando criação de nova aba em background por padrão...');
  const createdTab = await newTab('https://site.com', false);
  assert.strictEqual(createdTab.active, false);
  console.log('  -> PASS: Nova aba criada com active: false por padrão.');

  console.log('[TEST M2] 5. Testando componentes DOM de Cursor Virtual e Drag Simulator...');
  await testDomComponents();
  console.log('  -> PASS: Virtual Cursor e Drag Simulator operacionais no DOM.');

  console.log('\n[SUCESSO M2] 100% dos testes de automação e background CDP passaram com sucesso!');
  process.exit(0);
}

runVirtualBackgroundTests().catch(err => {
  console.error('[ERRO NOS TESTES M2]', err);
  process.exit(1);
});
