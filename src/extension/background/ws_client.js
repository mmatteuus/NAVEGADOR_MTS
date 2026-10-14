/**
 * @file ws_client.js
 * @description Cliente WebSocket resiliente para conexão com o Desktop App (porta 3456).
 * 
 * Implementa auto-cura permanente com backoff exponencial, handshake de entrada
 * e orquestração de comandos recebidos pelo servidor local.
 */

import { WS_URL, RECONNECT_BACKOFF_STEPS_MS, CONNECTION_STATE } from '../common/constants.js';
import { logger } from '../common/logger.js';
import { buildClientHello } from '../common/protocol.js';
import { updateConnectionStatus, setComputerUseAllowed, isAutomationEnabled } from './state_storage.js';
import { getActiveTab } from './tab_manager.js';
import { createHeartbeatManager } from './ws_heartbeat.js';

let socket = null;
let reconnectAttempt = 0;
let reconnectTimer = null;
let messageDispatcherFn = null;

const heartbeat = createHeartbeatManager(() => {
  cleanupSocket();
  scheduleReconnect();
});

export function setCommandDispatcher(dispatcher) {
  messageDispatcherFn = dispatcher;
}

export async function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const enabled = await isAutomationEnabled();
  if (!enabled) {
    logger.warn('Automação desabilitada pelo usuário. Conexão em repouso.');
    await updateConnectionStatus(CONNECTION_STATE.DISCONNECTED, 0);
    return;
  }

  await updateConnectionStatus(CONNECTION_STATE.CONNECTING, 0);
  logger.info(`Conectando ao Desktop App em ${WS_URL}...`);

  try {
    socket = new WebSocket(WS_URL);

    socket.onopen = async () => {
      logger.info('Conexão WebSocket estabelecida com sucesso.');
      reconnectAttempt = 0;
      await updateConnectionStatus(CONNECTION_STATE.CONNECTED, 0);

      const active = await getActiveTab();
      sendMessage(buildClientHello(active ? { id: active.id, url: active.url, title: active.title } : null));
      heartbeat.start();
    };

    socket.onmessage = (event) => handleIncomingMessage(event.data);

    socket.onclose = () => {
      logger.warn('Conexão WebSocket encerrada. Agendando reconexão resiliente...');
      cleanupSocket();
      scheduleReconnect();
    };

    socket.onerror = (err) => logger.debug('Falha de transporte no WebSocket:', err);
  } catch (err) {
    logger.error('Erro na instanciação do WebSocket:', err);
    scheduleReconnect();
  }
}

function handleIncomingMessage(rawData) {
  try {
    const msg = JSON.parse(rawData);

    if (msg.type === 'ping') {
      const { pongPayload, latencyMs } = heartbeat.handlePing(msg.ts);
      updateConnectionStatus(CONNECTION_STATE.CONNECTED, latencyMs);
      sendMessage(pongPayload);
      return;
    }

    if (msg.type === 'server_hello') {
      logger.info('Handshake confirmado pelo Desktop App:', msg.payload?.desktopVersion);
      if (typeof msg.payload?.computerUseAuthorized === 'boolean') {
        setComputerUseAllowed(msg.payload.computerUseAuthorized);
      }
      return;
    }

    if (typeof messageDispatcherFn === 'function') {
      messageDispatcherFn(msg);
    }
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

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  const delayIndex = Math.min(reconnectAttempt, RECONNECT_BACKOFF_STEPS_MS.length - 1);
  const delayMs = RECONNECT_BACKOFF_STEPS_MS[delayIndex];
  reconnectAttempt++;

  updateConnectionStatus(CONNECTION_STATE.RECONNECTING, 0);
  logger.info(`Reconexão agendada em ${delayMs}ms (Tentativa ${reconnectAttempt}).`);
  reconnectTimer = setTimeout(() => connectWebSocket(), delayMs);
}

function cleanupSocket() {
  heartbeat.stop();
  if (socket) {
    socket.onopen = null;
    socket.onmessage = null;
    socket.onclose = null;
    socket.onerror = null;
    try { socket.close(); } catch (_) {}
    socket = null;
  }
}

export function ensureConnected() {
  if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
    connectWebSocket();
  }
}
