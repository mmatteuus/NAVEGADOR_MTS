/**
 * @file command_dispatcher.js
 * @description Roteador central e filas assíncronas concorrentes de execução por sessão.
 */
import { logger } from '../common/logger.js';
import { buildActionResponse } from '../common/protocol.js';
import { TAB_ACTIONS } from '../common/constants.js';
import { isAutomationEnabled, incrementCommandCount } from './state_storage.js';
import { navigate, newTab, closeTab, switchTab, goBack, goForward } from './tab_manager.js';
import { requireGranted, targetId, popupGrantState, isGrantableUrl } from './tab_access.js';
import { captureTabScreenshot } from './screenshot_capture.js';
import { sendMessage, getConnectionToken } from './ws_client.js';
import { evaluatePageScript } from './page_script_executor.js';
import { requireContentSuccess } from './content_response.js';
import { enqueueSessionCommand } from './session_queues.js';
import { releaseTabFromSession } from './session_registry.js';
import { getSessionCookies, setSessionCookie, clearSessionCookies, clearSessionStorage } from './cookie_isolator.js';
import { isUpdateAdmissionBlocked } from './ws_update.js';

export function dispatchIncomingCommand(message) {
  const reqId = message.id || message.payload?.requestId || message.params?.requestId || `cmd_${Date.now()}`;
  const sessionId = message.sessionId || message.payload?.sessionId || message.params?.sessionId || null;
  const action = message.action || message.type || '', params = message.payload || message.params || {};
  const connectionToken = getConnectionToken();
  if (isUpdateAdmissionBlocked()) {
    const response = buildActionResponse(reqId, false, null, 'EXTENSION_UPDATE_PENDING: aguardando recarga segura.');
    if (sessionId) response.sessionId = sessionId;
    sendMessage(response, connectionToken);
    return;
  }

  const queued = enqueueSessionCommand(sessionId, async () => {
    try {
      if (!(await isAutomationEnabled())) throw new Error('Automação web desativada pelo usuário no painel do BROWSER MTS.');
      logger.info(`Executando comando '${action}' (ID: ${reqId}, Sessão: ${sessionId || 'global'}).`);
      if (getConnectionToken() !== connectionToken) throw new Error('CONNECTION_CHANGED: comando pendente descartado.');
      const result = await routeAction(action, params, sessionId);
      await incrementCommandCount();
      const resp = buildActionResponse(reqId, true, result, null);
      if (sessionId) resp.sessionId = sessionId;
      sendMessage(resp, connectionToken);
    } catch (err) {
      logger.error(`Falha na execução de '${action}':`, err.message);
      const resp = buildActionResponse(reqId, false, null, err.message);
      if (sessionId) resp.sessionId = sessionId;
    sendMessage(resp, connectionToken);
    }
  });
  queued.catch((err) => {
    logger.error(`Falha inesperada na fila de '${action}':`, err?.message || err);
    const resp = buildActionResponse(reqId, false, null, err?.message || 'Falha interna na fila.');
    if (sessionId) resp.sessionId = sessionId;
    sendMessage(resp, connectionToken);
  });
}

async function routeAction(action, params, sid) {
  if (action === 'browser_manage_tabs') return executeTabManagement(params, sid);
  if (action === 'browser_evaluate_js') return evaluatePageScript(await targetId(params.tabId, sid), params.script);
  if (action === 'browser_get_cookies') return getSessionCookies(sid, params);
  if (action === 'browser_set_cookie') return setSessionCookie(sid, params);
  if (action === 'browser_clear_cookies') return clearSessionCookies(sid, params?.url || params);
  if (action === 'browser_clear_storage' || action === 'browser_clear_session') return clearSessionStorage(sid);
  if (TAB_ACTIONS.includes(action)) return executeTabAction(action, params, sid);
  if (action === 'browser_screenshot' || action === 'screenshot_page' || action === 'screenshot_tab') {
    return captureTabScreenshot(params.format, params.quality, await targetId(params.tabId, sid));
  }
  return sendToContentScript(action, { ...params, tabId: await targetId(params.tabId, sid) }, sid);
}

async function createTab(url, active, sid, incognito = false) {
  if (url && !isGrantableUrl(url)) throw new Error('URL_NOT_ALLOWED');
  if (incognito && typeof chrome !== 'undefined' && chrome.windows?.create) {
    const win = await chrome.windows.create({ url: url || 'about:blank', incognito: true, focused: active === true });
    const tab = win.tabs?.[0] || { id: win.id };
    return { success: true, tabId: tab.id, windowId: win.id, incognito: true, url,
      requiresAssignment: true };
  }
  const tab = await newTab(url, active === true);
  return { ...tab, requiresAssignment: true };
}

const removeTab = async (tid, sid) => {
  const tab = await requireGranted(tid, sid), res = await closeTab(tab.id);
  releaseTabFromSession(tab.id);
  return res;
};
const focusTab = async (tid, win, sid) => {
  await requireGranted(tid, sid);
  return switchTab(await targetId(tid, sid), win === true);
};

async function executeTabManagement(p, sid) {
  switch (p.action) {
    case 'list': return popupGrantState(p.currentWindowOnly !== false, sid);
    case 'new': return createTab(p.url, p.active, sid, p.incognito === true);
    case 'switch': return focusTab(p.tabId, p.focusWindow, sid);
    case 'close': return removeTab(p.tabId, sid);
    default: throw new Error(`Ação de abas não reconhecida: ${p.action || 'N/A'}`);
  }
}
async function executeTabAction(act, p, sid) {
  switch (act) {
    case 'browser_navigate':
      if (!isGrantableUrl(p.url)) throw new Error('URL_NOT_ALLOWED');
      return navigate(p.url, await targetId(p.tabId, sid), p.active === true);
    case 'browser_new_tab': return createTab(p.url, p.active, sid, p.incognito === true);
    case 'browser_close_tab': return removeTab(p.tabId, sid);
    case 'browser_switch_tab': return focusTab(p.tabId, p.focusWindow, sid);
    case 'browser_list_tabs': return popupGrantState(p.currentWindowOnly !== false, sid);
    case 'browser_go_back': return goBack(await targetId(p.tabId, sid));
    case 'browser_go_forward': return goForward(await targetId(p.tabId, sid));
    default: throw new Error(`Ação de aba não reconhecida: ${act}`);
  }
}

const CS_FILES = [
  'content/content_bridge.js', 'content/dom_extractor.js', 'content/element_finder.js', 'content/interaction_extras.js',
  'content/virtual_key_press.js', 'content/interaction_simulator.js', 'content/keyboard_scroll.js',
  'content/eval_runner.js', 'content/virtual_cursor.js', 'content/drag_simulator.js'
];

async function sendToContentScript(action, params, sid) {
  const targetTab = await requireGranted(params.tabId, sid);
  try {
    return requireContentSuccess(await chrome.tabs.sendMessage(targetTab.id, { action, params }));
  } catch (err) {
    const missingReceiver = /receiving end|Could not establish connection|Receiving end does not exist/i.test(String(err?.message || err));
    if (!missingReceiver) throw err;
    logger.warn(`Injetando content scripts dinamicamente na aba ID ${targetTab.id}...`);
    await chrome.scripting.executeScript({ target: { tabId: targetTab.id }, files: CS_FILES });
    await requireGranted(params.tabId, sid);
    return requireContentSuccess(await chrome.tabs.sendMessage(targetTab.id, { action, params }));
  }
}
