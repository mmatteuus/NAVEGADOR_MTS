/**
 * @file command_dispatcher.js
 * @description Roteador central e fila sequencial de execução de comandos do agente.
 * Garante execução ordenada, roteando entre API de abas, CDP e Content Scripts.
 */

import { logger } from '../common/logger.js';
import { buildActionResponse } from '../common/protocol.js';
import { TAB_ACTIONS } from '../common/constants.js';
import { isAutomationEnabled, incrementCommandCount } from './state_storage.js';
import { navigate, newTab, closeTab, switchTab, goBack, goForward } from './tab_manager.js';
import { requireGranted, targetId, popupGrantState, isGrantableUrl } from './tab_access.js';
import { captureTabScreenshot } from './screenshot_capture.js';
import { sendMessage } from './ws_client.js';
import { evaluatePageScript } from './page_script_executor.js';
import { requireContentSuccess } from './content_response.js';

let commandQueue = Promise.resolve();

/**
 * Ponto de entrada para comandos recebidos pelo cliente WebSocket.
 * @param {object} message - Objeto da mensagem recebida.
 */
export function dispatchIncomingCommand(message) {
  const reqId = message.id || message.payload?.requestId || `cmd_${Date.now()}`;
  const action = message.action || message.type || '';
  const params = message.payload || message.params || {};

  commandQueue = commandQueue.then(async () => {
    try {
      const allowed = await isAutomationEnabled();
      if (!allowed) {
        throw new Error('Automação web desativada pelo usuário no painel do BROWSER MTS.');
      }

      logger.info(`Executando comando '${action}' (ID: ${reqId}).`);
      const result = await routeAction(action, params);
      await incrementCommandCount();
      sendMessage(buildActionResponse(reqId, true, result, null));
    } catch (err) {
      logger.error(`Falha na execução de '${action}':`, err.message);
      sendMessage(buildActionResponse(reqId, false, null, err.message));
    }
  });
}

/** Roteia a ação para o módulo especialista adequado. */
async function routeAction(action, params) {
  if (action === 'browser_manage_tabs') {
    return executeTabManagement(params);
  }
  if (action === 'browser_evaluate_js') {
    return evaluatePageScript(await targetId(params.tabId), params.script);
  }
  if (TAB_ACTIONS.includes(action)) {
    return executeTabAction(action, params);
  }
  if (action === 'browser_screenshot' || action === 'screenshot_page' || action === 'screenshot_tab') {
    return captureTabScreenshot(params.format, params.quality, await targetId(params.tabId));
  }
  return sendToContentScript(action, { ...params, tabId: await targetId(params.tabId) });
}

/** Executa a operação composta de abas mantendo background por padrão. */
async function executeTabManagement(params) {
  switch (params.action) {
    case 'list':
      return popupGrantState(params.currentWindowOnly !== false);
    case 'new':
      if (params.url && !isGrantableUrl(params.url)) throw new Error('URL_NOT_ALLOWED');
      return newTab(params.url, params.active === true);
    case 'switch':
      await requireGranted(params.tabId);
      return switchTab(await targetId(params.tabId), params.focusWindow === true);
    case 'close':
      const tab = await requireGranted(params.tabId);
      const result = await closeTab(tab.id);
      return result;
    default:
      throw new Error(`Ação de abas não reconhecida: ${params.action || 'N/A'}`);
  }
}

/** Executa ações no nível do gerenciador de abas. */
async function executeTabAction(action, params) {
  switch (action) {
    case 'browser_navigate':
      if (!isGrantableUrl(params.url)) throw new Error('URL_NOT_ALLOWED');
      return navigate(params.url, await targetId(params.tabId), params.active === true);
    case 'browser_new_tab':
      if (params.url && !isGrantableUrl(params.url)) throw new Error('URL_NOT_ALLOWED');
      return newTab(params.url, params.active === true);
    case 'browser_close_tab':
      const tab = await requireGranted(params.tabId);
      return closeTab(tab.id);
    case 'browser_switch_tab':
      await requireGranted(params.tabId);
      return switchTab(await targetId(params.tabId), params.focusWindow === true);
    case 'browser_list_tabs':
      return popupGrantState(params.currentWindowOnly !== false);
    case 'browser_go_back':
      return goBack(await targetId(params.tabId));
    case 'browser_go_forward':
      return goForward(await targetId(params.tabId));
    default:
      throw new Error(`Ação de aba não reconhecida: ${action}`);
  }
}

/** Encaminha comandos de inspeção e interação para o Content Script da aba. */
async function sendToContentScript(action, params) {
  const targetTab = await requireGranted(params.tabId);

  let response;
  try {
    response = await chrome.tabs.sendMessage(targetTab.id, { action, params });
  } catch (_err) {
    logger.warn(`Injetando content scripts dinamicamente na aba ID ${targetTab.id}...`);
    await requireGranted(targetTab.id);
    await chrome.scripting.executeScript({
      target: { tabId: targetTab.id },
      files: [
        'content/content_bridge.js',
        'content/dom_extractor.js',
        'content/element_finder.js',
        'content/interaction_extras.js',
        'content/virtual_key_press.js',
        'content/interaction_simulator.js',
        'content/keyboard_scroll.js',
        'content/eval_runner.js',
        'content/virtual_cursor.js',
        'content/drag_simulator.js'
      ]
    });
    response = await chrome.tabs.sendMessage(targetTab.id, { action, params });
  }
  return requireContentSuccess(response);
}
