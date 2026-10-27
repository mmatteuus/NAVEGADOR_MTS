/**
 * @file logger.js
 * @description Módulo de registro de logs padronizado da extensão Browser MTS.
 *
 * Fornece formatação uniforme com prefixo [BrowserMTS], carimbo de data/hora
 * em formato ISO e separação por níveis de severidade (debug, info, warn, error).
 */

const PREFIX = '[BrowserMTS]';

/**
 * Retorna o carimbo de data e hora atual em formato legível UTC.
 * @returns {string} Timestamp no formato ISO.
 */
function getTimestamp() {
  return new Date().toISOString();
}

/**
 * Registrador de logs estruturado para facilitar depuração no DevTools.
 */
export const logger = {
  /**
   * Registra mensagem informativa geral.
   * @param {string} message - Texto descritivo.
   * @param {...any} args - Dados adicionais para inspeção.
   */
  info(message, ...args) {
    console.log(`${PREFIX} [INFO] [${getTimestamp()}] ${message}`, ...args);
  },

  /**
   * Registra aviso operacional que não impede o fluxo.
   * @param {string} message - Texto do aviso.
   * @param {...any} args - Detalhes do contexto.
   */
  warn(message, ...args) {
    console.warn(`${PREFIX} [WARN] [${getTimestamp()}] ${message}`, ...args);
  },

  /**
   * Registra falha ou exceção capturada.
   * @param {string} message - Descrição do erro.
   * @param {...any} args - Objeto de erro ou rastreamento.
   */
  error(message, ...args) {
    console.error(`${PREFIX} [ERROR] [${getTimestamp()}] ${message}`, ...args);
  },

  /**
   * Registra dados detalhados para depuração aprofundada de mensagens de rede.
   * @param {string} message - Detalhes do evento.
   * @param {...any} args - Payloads brutos.
   */
  debug(message, ...args) {
    console.debug(`${PREFIX} [DEBUG] [${getTimestamp()}] ${message}`, ...args);
  }
};
