/**
 * @file test_extension_adversarial.mjs
 * @description Suíte de testes adversariais para a Extensão MV3 do BROWSER MTS.
 * 
 * Validações de cenários de borda:
 * 1. Bloqueio preventivo de screenshot em URLs restritas (chrome://, edge://).
 * 2. Prevenção de fechamento da janela ao fechar a última aba restante.
 * 3. Enfileiramento e serialização sob burst de 30 comandos concorrentes.
 * 4. Rejeição imediata quando automação estiver desabilitada no storage.
 */

import assert from 'node:assert';

// Setup de Mocks Globais da API chrome.* e WebSocket ANTES dos imports
const mockStorage = { browser_mts_automation_enabled: true };
let openTabs = [{ id: 101, url: 'https://example.com', title: 'Example', active: true, windowId: 1 }];
const sentWsMessages = [];

class MockWebSocket {
  static OPEN = 1;
  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.OPEN;
    setTimeout(() => { if (this.onopen) this.onopen(); }, 5);
  }
  send(data) {
    sentWsMessages.push(JSON.parse(data));
  }
  close() {
    this.readyState = 3;
    if (this.onclose) this.onclose();
  }
}

globalThis.WebSocket = MockWebSocket;
globalThis.chrome = {
  storage: {
    local: {
      get: async (k) => (typeof k === 'string' ? { [k]: mockStorage[k] } : mockStorage),
      set: async (obj) => Object.assign(mockStorage, obj)
    }
  },
  tabs: {
    query: async (q) => openTabs.filter(t => (q.active ? t.active : true)),
    create: async (opts) => {
      const newT = { id: Math.floor(Math.random() * 1000) + 200, ...opts, windowId: 1 };
      openTabs.push(newT);
      return newT;
    },
    remove: async (id) => {
      openTabs = openTabs.filter(t => t.id !== id);
    },
    update: async (id, props) => {
      const t = openTabs.find(tab => tab.id === id);
      if (t) Object.assign(t, props);
      return t || { id, ...props };
    },
    sendMessage: async (tabId, msg) => {
      const tab = openTabs.find(t => t.id === tabId);
      if (tab?.url?.startsWith('chrome://')) {
        throw new Error('Acesso negado: não é permitido injetar scripts em páginas chrome://');
      }
      return { received: true, action: msg.action };
    },
    captureVisibleTab: async (_winId, _opts) => 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
  },
  scripting: {
    executeScript: async ({ target }) => {
      const tab = openTabs.find(t => t.id === target.tabId);
      if (tab?.url?.startsWith('chrome://')) {
        throw new Error('Scripting não permitido em chrome://');
      }
      return [{ result: true }];
    }
  }
};

const { captureTabScreenshot } = await import('../src/extension/background/screenshot_capture.js');
const { closeTab } = await import('../src/extension/background/tab_manager.js');
const { dispatchIncomingCommand } = await import('../src/extension/background/command_dispatcher.js');
const { setAutomationEnabled } = await import('../src/extension/background/state_storage.js');
const { connectWebSocket } = await import('../src/extension/background/ws_client.js');

async function runAdversarialExtensionTests() {
  await connectWebSocket();
  await new Promise(r => setTimeout(r, 20)); // Conexão WS mockada

  console.log('[TEST] 1. Testando bloqueio de screenshot em URLs restritas (chrome://)...');
  openTabs = [{ id: 10, url: 'chrome://settings', title: 'Configurações', active: true, windowId: 1 }];
  await assert.rejects(
    async () => captureTabScreenshot('png'),
    /URLs internas do sistema/,
    'Screenshot em chrome:// deveria ter sido expressamente rejeitado!'
  );
  console.log('  -> PASS: URLs internas protegidas com erro descritivo.');

  console.log('[TEST] 2. Testando fechamento da última aba (prevenção de queda do browser)...');
  openTabs = [{ id: 99, url: 'https://site.com', active: true, windowId: 1 }];
  await closeTab(99);
  const hasBlank = openTabs.some(t => t.url === 'about:blank');
  assert.ok(hasBlank, 'Deveria ter mantido o navegador aberto criando about:blank!');
  console.log('  -> PASS: Prevenção de fechamento total do browser validada.');

  console.log('[TEST] 3. Testando burst de 30 comandos concorrentes no Command Dispatcher...');
  openTabs = [{ id: 1, url: 'https://app.test', active: true, windowId: 1 }];
  sentWsMessages.length = 0;
  for (let i = 0; i < 30; i++) {
    dispatchIncomingCommand({ id: `burst_${i}`, action: 'browser_get_text', params: { selector: 'body' } });
  }
  await new Promise(resolve => setTimeout(resolve, 300));
  assert.strictEqual(sentWsMessages.length, 30, 'Todos os 30 comandos devem ser despachados.');
  for (let i = 0; i < 30; i++) {
    const resp = sentWsMessages.find(m => m.id === `burst_${i}`);
    assert.ok(resp, `Resposta para burst_${i} ausente!`);
    assert.strictEqual(resp.success, true);
  }
  console.log('  -> PASS: Fila serializou com sucesso 30 comandos em rajada sem corrida.');

  console.log('[TEST] 4. Testando rejeição imediata quando automação estiver desativada...');
  await setAutomationEnabled(false);
  sentWsMessages.length = 0;
  dispatchIncomingCommand({ id: 'blocked_cmd', action: 'browser_click', params: { selector: '#btn' } });
  await new Promise(resolve => setTimeout(resolve, 50));
  assert.strictEqual(sentWsMessages.length, 1);
  assert.strictEqual(sentWsMessages[0].success, false);
  assert.match(sentWsMessages[0].error, /Automação web desativada pelo usuário/);
  console.log('  -> PASS: Comandos rejeitados corretamente quando desativado.');
  await setAutomationEnabled(true);

  console.log('\n[SUCESSO] Todos os 4 testes de cenários de borda da Extensão MV3 passaram com louvor!');
  process.exit(0);
}

runAdversarialExtensionTests().catch(err => {
  console.error('[FALHA NO TESTE DA EXTENSÃO]', err);
  process.exit(1);
});
