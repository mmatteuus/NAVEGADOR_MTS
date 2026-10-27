/**
 * @file ws_heartbeat.js
 * @description Gerenciador bidirecional de Heartbeat e Keep-Alive para Service Worker MV3.
 *
 * Envia pings ativos a cada 4 segundos, previne a suspensão de 30s do Service Worker
 * do Chromium e monitora o timeout de forma resiliente para evitar falsas desconexões.
 */

import { HEARTBEAT_INTERVAL_MS, HEARTBEAT_TIMEOUT_MS } from '../common/constants.js';
import { logger } from '../common/logger.js';
import { buildHeartbeatPong, buildHeartbeatPing } from '../common/protocol.js';

/**
 * Cria o gerenciador de pulso de heartbeat bidirecional.
 * @param {Function} onTimeout - Callback executado quando o servidor ficar mudo.
 * @param {Function} [sendPingFn=null] - Função para despacho do pacote de ping.
 * @returns {object} Métodos do gerenciador.
 */
export function createHeartbeatManager(onTimeout, sendPingFn = null) {
  let heartbeatTimer = null;
  let lastHeartbeatTs = Date.now();

  /**
   * Inicia o ciclo periódico de pulso ativo e monitoramento.
   */
  function start() {
    lastHeartbeatTs = Date.now();
    stop();

    heartbeatTimer = setInterval(() => {
      // 1. Envia ping ativo pelo WebSocket
      if (typeof sendPingFn === 'function') {
        sendPingFn(buildHeartbeatPing());
      }

      // 2. Acorda o Service Worker na API do Chrome para resetar o timer de 30s
      try {
        if (typeof chrome !== 'undefined' && chrome.runtime?.getPlatformInfo) {
          chrome.runtime.getPlatformInfo(() => {});
        }
      } catch (_) {}

      // 3. Verifica tolerância de resposta (20s sem nenhum retorno)
      if (Date.now() - lastHeartbeatTs > HEARTBEAT_TIMEOUT_MS) {
        logger.warn(`Silêncio na ponte WebSocket (> ${HEARTBEAT_TIMEOUT_MS / 1000}s). Reconectando...`);
        stop();
        if (typeof onTimeout === 'function') {
          onTimeout();
        }
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  /**
   * Registra recebimento de pong do Desktop App e calcula latência.
   * @param {number} serverTs - Carimbo enviado no ping.
   * @returns {number} Latência em milissegundos.
   */
  function handlePong(serverTs) {
    lastHeartbeatTs = Date.now();
    return serverTs ? Math.max(1, Date.now() - serverTs) : 5;
  }

  /**
   * Trata ping recebido do Desktop App respondendo com pong.
   * @param {number} serverTs - Carimbo de data/hora do servidor.
   * @returns {{ pongPayload: object, latencyMs: number }} Resposta e latência.
   */
  function handlePing(serverTs) {
    lastHeartbeatTs = Date.now();
    const latencyMs = serverTs ? Math.max(1, Date.now() - serverTs) : 5;
    return {
      pongPayload: buildHeartbeatPong(serverTs),
      latencyMs
    };
  }

  /**
   * Encerra o timer de heartbeat.
   */
  function stop() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  return {
    start,
    handlePong,
    handlePing,
    stop
  };
}
