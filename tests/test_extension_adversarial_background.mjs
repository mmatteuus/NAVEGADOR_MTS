/**
 * @file test_extension_adversarial_background.mjs
 * @description Testes adversariais de background sem roubo de foco (focusWindow: false).
 */
import assert from 'node:assert';

const windowFocusCalls = [];
const tabUpdateCalls = [];
const sentWsMessages = [];
let cdpScreenshotCalled = false;
let cdpShouldFail = false;

const tabsList = [
  { id: 10, url: 'https://site-ativo.com', active: true, windowId: 100 },
  { id: 20, url: 'https://site-background.com', active: false, windowId: 100 }
];

class MockWebSocket {
  static OPEN = 1;
  constructor() {
    this.readyState = MockWebSocket.OPEN;
    setTimeout(() => { if (this.onopen) this.onopen(); }, 5);
  }
  send(data) { sentWsMessages.push(JSON.parse(data)); }
  close() { this.readyState = 3; }
}

globalThis.WebSocket = MockWebSocket;
globalThis.chrome = {
  debugger: {
    attach: async () => {},
    detach: async () => {},
    sendCommand: async (_t, method) => {
      if (method === 'Page.captureScreenshot') {
        cdpScreenshotCalled = true;
        if (cdpShouldFail) throw new Error('Simulated CDP screenshot error');
        return { data: 'BASE64_BG_SCREENSHOT' };
      }
      return { success: true };
    },
    onDetach: { addListener: () => {} }
  },
  windows: {
    update: async (windowId, info) => {
      windowFocusCalls.push({ windowId, info });
      return { id: windowId, ...info };
    }
  },
  tabs: {
    get: async (id) => tabsList.find(t => t.id === id),
    query: async (q) => tabsList.filter(t => (q.active ? t.active : true)),
    create: async (opts) => {
      const tab = { id: 30 + tabsList.length, ...opts, windowId: 100 };
      tabsList.push(tab);
      return tab;
    },
    update: async (id, props) => {
      tabUpdateCalls.push({ id, props });
      const t = tabsList.find(tab => tab.id === id);
      if (t) Object.assign(t, props);
      return t || { id, ...props };
    },
    captureVisibleTab: async () => 'data:image/png;base64,FALLBACK_SCREENSHOT'
  },
  storage: { local: { get: async () => ({ browser_mts_automation_enabled: true }), set: async () => {} } }
};

const { captureTabScreenshot } = await import('../src/extension/background/screenshot_capture.js');
const { dispatchIncomingCommand } = await import('../src/extension/background/command_dispatcher.js');
const { connectWebSocket } = await import('../src/extension/background/ws_client.js');

async function testAdversarialBackground() {
  await connectWebSocket();
  await new Promise(r => setTimeout(r, 20));

  console.log('[TEST BG] 1. Captura de tela de aba background nao foca janela...');
  windowFocusCalls.length = 0;
  tabUpdateCalls.length = 0;
  cdpScreenshotCalled = false;

  const resDirect = await captureTabScreenshot('png', 90, 20);
  assert.strictEqual(resDirect.success, true);
  assert.strictEqual(resDirect.tabId, 20);
  assert.strictEqual(cdpScreenshotCalled, true);
  assert.strictEqual(windowFocusCalls.length, 0, 'Janela nao pode ter sido focada!');
  assert.strictEqual(tabUpdateCalls.some(c => c.id === 20 && c.props.active === true), false);

  console.log('[TEST BG] 2. Despacho browser_screenshot via Command Dispatcher...');
  sentWsMessages.length = 0;
  dispatchIncomingCommand({ id: 'cmd_shot', action: 'browser_screenshot', params: { tabId: 20 } });
  await new Promise(r => setTimeout(r, 60));
  const shotResp = sentWsMessages.find(m => m.id === 'cmd_shot');
  assert.ok(shotResp && shotResp.success);
  assert.strictEqual(shotResp.data.tabId, 20);
  assert.strictEqual(windowFocusCalls.length, 0);

  console.log('[TEST BG] 3. Fallback de captura quando CDP falha...');
  cdpShouldFail = true;
  const fallbackRes = await captureTabScreenshot('png', 90, 10);
  assert.strictEqual(fallbackRes.success, true);
  assert.strictEqual(fallbackRes.base64, 'FALLBACK_SCREENSHOT');
  cdpShouldFail = false;

  console.log('[TEST BG] 4. switch com focusWindow: false vs focusWindow: true...');
  windowFocusCalls.length = 0;
  sentWsMessages.length = 0;
  dispatchIncomingCommand({
    id: 'cmd_sw_bg', action: 'browser_manage_tabs',
    params: { action: 'switch', tabId: 20, focusWindow: false }
  });
  await new Promise(r => setTimeout(r, 60));
  assert.strictEqual(windowFocusCalls.length, 0, 'focusWindow: false nao deve focar janela');

  dispatchIncomingCommand({
    id: 'cmd_sw_fg', action: 'browser_manage_tabs',
    params: { action: 'switch', tabId: 20, focusWindow: true }
  });
  await new Promise(r => setTimeout(r, 60));
  assert.strictEqual(windowFocusCalls.length, 1);
  assert.strictEqual(windowFocusCalls[0].info.focused, true);

  console.log('\n[SUCESSO BG] 100% dos testes adversariais de background passaram!');
  process.exit(0);
}

testAdversarialBackground().catch(err => {
  console.error('[FALHA NO TESTE ADVERSARIAL BG]', err);
  process.exit(1);
});
