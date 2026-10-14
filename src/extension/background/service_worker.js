/**
 * @file service_worker.js
 * @description Ponto de entrada do Service Worker em segundo plano (Manifest V3).
 * 
 * Orquestra o ciclo de vida da extensão, inicializa a escuta contra suspensão
 * de 30s, abre a conexão com o Desktop App e atende requisições do Popup.
 */

import { logger } from '../common/logger.js';
import { STORAGE_KEYS, CONNECTION_STATE } from '../common/constants.js';
import { initKeepAlive } from './keep_alive.js';
import { connectWebSocket, ensureConnected, setCommandDispatcher } from './ws_client.js';
import { dispatchIncomingCommand } from './command_dispatcher.js';
import { isAutomationEnabled, setAutomationEnabled } from './state_storage.js';

logger.info('Service Worker do BROWSER MTS inicializado.');

// 1. Liga o despachante de comandos ao cliente WebSocket
setCommandDispatcher(dispatchIncomingCommand);

// 2. Registra o mecanismo triplo keep-alive com verificação contínua
initKeepAlive(() => {
  ensureConnected();
});

// 3. Evento disparado na instalação ou atualização da extensão
chrome.runtime.onInstalled.addListener(async (details) => {
  logger.info(`Extensão instalada/atualizada. Motivo: ${details.reason}.`);
  const enabled = await isAutomationEnabled();
  if (enabled) {
    connectWebSocket();
  }
});

// 4. Evento disparado na inicialização do navegador
chrome.runtime.onStartup.addListener(async () => {
  logger.info('Navegador iniciado. Verificando conexão com o Desktop App...');
  const enabled = await isAutomationEnabled();
  if (enabled) {
    connectWebSocket();
  }
});

// 5. Atende mensagens internas vindas do Popup da extensão
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'GET_POPUP_STATE') {
    chrome.storage.local.get(null).then((data) => {
      sendResponse({
        success: true,
        data: {
          automationEnabled: data[STORAGE_KEYS.AUTOMATION_ENABLED] !== false,
          connectionStatus: data[STORAGE_KEYS.CONNECTION_STATUS] || CONNECTION_STATE.DISCONNECTED,
          latencyMs: data[STORAGE_KEYS.LAST_LATENCY_MS] || 0,
          computerUseAllowed: !!data[STORAGE_KEYS.COMPUTER_USE_ALLOWED],
          totalCommands: data[STORAGE_KEYS.TOTAL_COMMANDS] || 0
        }
      });
    });
    return true; // Retorno assíncrono para chrome.runtime.onMessage
  }

  if (message.type === 'TOGGLE_AUTOMATION') {
    const nextState = !!message.enabled;
    setAutomationEnabled(nextState).then(() => {
      if (nextState) {
        connectWebSocket();
      }
      sendResponse({ success: true, enabled: nextState });
    });
    return true;
  }

  if (message.type === 'RECONNECT_NOW') {
    connectWebSocket().then(() => {
      sendResponse({ success: true });
    });
    return true;
  }
});

// Inicialização imediata ao carregar o script
connectWebSocket();
