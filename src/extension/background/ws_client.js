/**
 * @file ws_client.js
 * @description Cliente WebSocket resiliente para conexão com o Desktop App (porta 3456).
 */

import { WS_BASE_URL, RECONNECT_BACKOFF_STEPS_MS, CONNECTION_STATE, STORAGE_KEYS } from '../common/constants.js';
import { logger } from '../common/logger.js';
import { createClientHello, installGrantSync } from './extension_identity.js';
import { updateConnectionStatus, setComputerUseAllowed, isAutomationEnabled } from './state_storage.js';
import { getActiveTab } from './tab_manager.js';
import { createHeartbeatManager } from './ws_heartbeat.js';
import { createPortRecovery } from './port_recovery.js';
let socket = null, reconnectAttempt = 0, reconnectTimer = null, messageDispatcherFn = null;
let connectionInProgress = false, connectionTimer = null, connectionId = 0;
const CONNECT_TIMEOUT_MS = 2000;
const portRecovery = createPortRecovery();
const heartbeat = createHeartbeatManager(
  () => { cleanupSocket(); scheduleReconnect(); },
  (pingMsg) => sendMessage(pingMsg)
);

export function setCommandDispatcher(dispatcher) { messageDispatcherFn = dispatcher; }
export async function connectWebSocket() {
  if (connectionInProgress || (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING))) return;
  connectionInProgress = true;
  const enabled = await isAutomationEnabled();
  if (!enabled) {
    connectionInProgress = false;
    await updateConnectionStatus(CONNECTION_STATE.DISCONNECTED, 0);
    return;
  }
  await portRecovery.load();
  const activePort = portRecovery.currentPort();
  const targetUrl = `${WS_BASE_URL}:${activePort}`;
  await updateConnectionStatus(CONNECTION_STATE.CONNECTING, 0);
  logger.info(`Conectando ao Desktop App em ${targetUrl}...`);
  try {
    const attemptId = ++connectionId;
    const candidate = new WebSocket(targetUrl);
    socket = candidate;
    connectionTimer = setTimeout(() => {
      const pending = candidate.readyState === 0 || candidate.readyState === WebSocket.CONNECTING;
      if (connectionId === attemptId && socket === candidate && pending) {
        logger.warn(`Tempo esgotado ao conectar em ${targetUrl}; testando recuperação.`);
        portRecovery.advance();
        cleanupSocket();
        connectionInProgress = false;
        scheduleReconnect(250);
      }
    }, CONNECT_TIMEOUT_MS);
    candidate.onopen = async () => {
      const isCurrent = () => connectionId === attemptId && socket === candidate;
      clearTimeout(connectionTimer); connectionTimer = null;
      connectionInProgress = false;
      logger.info(`WebSocket conectado com sucesso na porta ${activePort}.`);
      reconnectAttempt = 0; portRecovery.markSuccess();
      await updateConnectionStatus(CONNECTION_STATE.CONNECTED, 0);
      if (!isCurrent()) return;
      try { await chrome.storage.local.set({ [STORAGE_KEYS.ACTIVE_PORT]: activePort }); } catch (_) {}
      if (!isCurrent()) return;
      const active = await getActiveTab();
      if (!isCurrent()) return;
      sendMessage(await createClientHello(active ? { id: active.id, url: active.url, title: active.title } : null));
      heartbeat.start();
    };
    candidate.onmessage = (event) => handleIncomingMessage(event.data);
    candidate.onclose = () => {
      if (connectionId !== attemptId) return;
      clearTimeout(connectionTimer); connectionTimer = null;
      connectionInProgress = false;
      logger.warn(`Conexão na porta ${activePort} encerrada. Tentando reconexão...`);
      portRecovery.advance();
      cleanupSocket(); scheduleReconnect();
    };
    candidate.onerror = (err) => logger.debug('Falha de transporte no WebSocket:', err);
  } catch (err) {
    connectionInProgress = false;
    logger.error('Erro na instanciação do WebSocket:', err);
    portRecovery.advance();
    scheduleReconnect(250);
  }
}
function handleIncomingMessage(rawData) {
  try {
    const msg = JSON.parse(rawData);
    if (msg.type === 'pong') {
      const lat = heartbeat.handlePong(msg.ts);
      updateConnectionStatus(CONNECTION_STATE.CONNECTED, lat);
      return;
    }
    if (msg.type === 'ping') {
      const { pongPayload, latencyMs } = heartbeat.handlePing(msg.ts);
      updateConnectionStatus(CONNECTION_STATE.CONNECTED, latencyMs);
      sendMessage(pongPayload);
      return;
    }
    if (msg.type === 'server_hello') {
      logger.info('Handshake confirmado pelo Desktop App:', msg.payload?.desktopVersion);
      if (typeof msg.payload?.computerUseAuthorized === 'boolean') setComputerUseAllowed(msg.payload.computerUseAuthorized);
      if (msg.payload?.extensionUpdateRequired && !msg.payload?.reloadRequired) {
        logger.warn(msg.payload.extensionUpdateMessage || 'A extensão está desatualizada; carregue a pasta instalada pelo aplicativo.');
      }
      if (msg.payload?.reloadRequired) chrome.runtime.reload();
      return;
    }
    if (msg.type === 'reload_extension' || msg.action === 'reload_extension') {
      logger.info('Auto-atualização da extensão solicitada pelo Desktop App.');
      chrome.runtime.reload();
      return;
    }
    if (typeof messageDispatcherFn === 'function') messageDispatcherFn(msg);
  } catch (err) {
    logger.error('Erro ao processar mensagem recebida:', err);
  }
}
export function sendMessage(payload) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  } else {
    logger.warn('Tentativa de envio com socket fechado ou em reconexão.');
  }
}

function scheduleReconnect(delayOverride = null) {
  clearTimeout(reconnectTimer);
  const delayMs = delayOverride ?? RECONNECT_BACKOFF_STEPS_MS[Math.min(reconnectAttempt++, RECONNECT_BACKOFF_STEPS_MS.length - 1)];
  updateConnectionStatus(CONNECTION_STATE.RECONNECTING, 0);
  reconnectTimer = setTimeout(() => { reconnectTimer = null; connectWebSocket(); }, delayMs);
}

function cleanupSocket() {
  heartbeat.stop();
  connectionInProgress = false;
  clearTimeout(connectionTimer); connectionTimer = null;
  if (socket) {
    socket.onopen = null; socket.onmessage = null; socket.onclose = null; socket.onerror = null;
    try { socket.close(); } catch (_) {}
    socket = null;
  }
}

export function ensureConnected() {
  if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) connectWebSocket();
}
installGrantSync(async () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  const active = await getActiveTab();
  sendMessage(await createClientHello(active ? { id: active.id, url: active.url, title: active.title } : null));
});
