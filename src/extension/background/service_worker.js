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
import { connectWebSocket, disconnectWebSocket, ensureConnected, isSocketConnected, setCommandDispatcher } from './ws_client.js';
import { dispatchIncomingCommand } from './command_dispatcher.js';
import { isAutomationEnabled, setAutomationEnabled } from './state_storage.js';
import { grantFromPopup, assignFromPopup, clearGrants, popupGrantState, openGrantedTab } from './tab_access.js';
import { getAgentDirectory } from './agent_directory.js';
import { getExtensionUpdateState } from './ws_update.js';

logger.info('Service Worker do BROWSER MTS inicializado.');
const isPopup = sender => sender?.url === chrome.runtime.getURL('popup/popup.html');

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
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_POPUP_STATE') {
    if (!isPopup(sender)) { sendResponse({ success: false, error: 'GRANT_FORBIDDEN' }); return false; }
    chrome.storage.local.get(null).then(async (data) => {
      const automationEnabled = await isAutomationEnabled();
      if (automationEnabled && !isSocketConnected()) ensureConnected();
      const tabGrants = await popupGrantState(), updateState = await getExtensionUpdateState();
      sendResponse({
        success: true,
        data: {
          automationEnabled,
          connectionStatus: data[STORAGE_KEYS.CONNECTION_STATUS] || CONNECTION_STATE.DISCONNECTED,
          latencyMs: data[STORAGE_KEYS.LAST_LATENCY_MS] || 0,
          computerUseAllowed: !!data[STORAGE_KEYS.COMPUTER_USE_ALLOWED],
          totalCommands: data[STORAGE_KEYS.TOTAL_COMMANDS] || 0,
          activePort: data[STORAGE_KEYS.ACTIVE_PORT] || 3456,
          tabGrants,
          agents: getAgentDirectory(),
          updateState
        }
      });
    });
    return true;
  }

  if (message.type === 'GET_TAB_GRANTS') {
    if (!isPopup(sender)) { sendResponse({ success: false, error: 'GRANT_FORBIDDEN' }); return false; }
    popupGrantState().then(tabGrants => sendResponse({ success: true, data: tabGrants, agents: getAgentDirectory() }));
    return true;
  }

  if (message.type === 'SAVE_TAB_GRANTS') {
    grantFromPopup(message, sender).then(() => popupGrantState())
      .then(tabGrants => sendResponse({ success: true, data: tabGrants }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (message.type === 'ASSIGN_TAB_GRANTS') {
    assignFromPopup(message, sender).then(() => popupGrantState())
      .then(data => sendResponse({ success: true, data }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (message.type === 'CLEAR_TAB_GRANTS') {
    if (!sender?.url || sender.url !== chrome.runtime.getURL('popup/popup.html')) {
      sendResponse({ success: false, error: 'GRANT_FORBIDDEN' });
    } else {
      clearGrants().then(() => popupGrantState())
        .then(tabGrants => sendResponse({ success: true, data: tabGrants }))
        .catch(error => sendResponse({ success: false, error: error.message }));
    }
    return true;
  }

  if (message.type === 'OPEN_GRANTED_TAB') {
    openGrantedTab(message, sender).then(tabGrants => sendResponse({ success: true, data: tabGrants }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (message.type === 'TOGGLE_AUTOMATION') {
    if (!isPopup(sender)) { sendResponse({ success: false, error: 'GRANT_FORBIDDEN' }); return false; }
    const nextState = !!message.enabled;
    setAutomationEnabled(nextState).then(() => {
      if (nextState) {
        connectWebSocket();
      } else {
        disconnectWebSocket();
      }
      sendResponse({ success: true, enabled: nextState });
    }).catch(error => sendResponse({ success: false, enabled: false, error: error.message }));
    return true;
  }

  if (message.type === 'RECONNECT_NOW') {
    if (!isPopup(sender)) { sendResponse({ success: false, error: 'GRANT_FORBIDDEN' }); return false; }
    connectWebSocket().then(() => {
      sendResponse({ success: true });
    });
    return true;
  }
});

// Inicialização imediata ao carregar o script
connectWebSocket();
