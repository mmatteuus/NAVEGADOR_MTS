/**
 * @file ws_heartbeat.js
 * @description Gerenciador de Heartbeat e monitor de timeout do WebSocket.
 * 
 * Controla os intervalos de verificação de 3 segundos e dispara reconexão
 * caso a conexão entre em estado silencioso ou congele por mais de 6 segundos.
 */

import { HEARTBEAT_INTERVAL_MS, HEARTBEAT_TIMEOUT_MS } from '../common/constants.js';
import { logger } from '../common/logger.js';
import { buildHeartbeatPong } from '../common/protocol.js';

/**
 * Cria uma instância do monitor de integridade de heartbeat.
 * @param {Function} onTimeout - Callback executado quando o heartbeat expirar.
 * @returns {object} Métodos de controle do monitor.
 */
export function createHeartbeatManager(onTimeout) {
  let heartbeatTimer = null;
  let lastPingReceivedTs = 0;

  /**
   * Inicia a verificação periódica de pings recebidos.
   */
  function start() {
    lastPingReceivedTs = Date.now();
    stop();
    heartbeatTimer = setInterval(() => {
      if (Date.now() - lastPingReceivedTs > HEARTBEAT_TIMEOUT_MS) {
        logger.warn('Timeout de heartbeat (6s sem ping). Forçando reconexão.');
        stop();
        if (typeof onTimeout === 'function') {
          onTimeout();
        }
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  /**
   * Registra o recebimento de um ping do Desktop App e calcula a latência.
   * @param {number} serverTs - Carimbo enviado pelo servidor.
   * @returns {{ pongPayload: object, latencyMs: number }} Resposta e latência.
   */
  function handlePing(serverTs) {
    lastPingReceivedTs = Date.now();
    const latencyMs = serverTs ? Math.max(1, Date.now() - serverTs) : 5;
    return {
      pongPayload: buildHeartbeatPong(serverTs),
      latencyMs
    };
  }

  /**
   * Encerra os timers ativos.
   */
  function stop() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  return {
    start,
    handlePing,
    stop
  };
}
