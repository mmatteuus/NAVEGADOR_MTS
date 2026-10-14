/**
 * @file state_storage.js
 * @description Gerenciamento de persistência de estado local da extensão.
 * 
 * Utiliza a API chrome.storage.local para reter preferências do usuário,
 * status de conexão, latência recente e contadores operacionais entre recargas.
 */

import { STORAGE_KEYS, CONNECTION_STATE } from '../common/constants.js';
import { logger } from '../common/logger.js';

/**
 * Consulta se a automação web está autorizada pelo usuário.
 * @returns {Promise<boolean>} Verdadeiro se a chave estiver ligada (padrão true).
 */
export async function isAutomationEnabled() {
  try {
    const data = await chrome.storage.local.get(STORAGE_KEYS.AUTOMATION_ENABLED);
    return data[STORAGE_KEYS.AUTOMATION_ENABLED] !== false;
  } catch (err) {
    logger.error('Falha ao ler permissão de automação do storage:', err);
    return true;
  }
}

/**
 * Atualiza o interruptor de automação (ligado/desligado) no storage.
 * @param {boolean} enabled - Novo estado do interruptor.
 */
export async function setAutomationEnabled(enabled) {
  try {
    await chrome.storage.local.set({ [STORAGE_KEYS.AUTOMATION_ENABLED]: !!enabled });
    logger.info(`Automação web ${enabled ? 'HABILITADA' : 'DESABILITADA'} pelo usuário.`);
  } catch (err) {
    logger.error('Erro ao persistir estado de automação:', err);
  }
}

/**
 * Atualiza o status atual de conexão e latência observada.
 * @param {string} status - Novo estado de conexão (ver CONNECTION_STATE).
 * @param {number} [latencyMs=0] - Latência recente em milissegundos.
 */
export async function updateConnectionStatus(status, latencyMs = 0) {
  try {
    await chrome.storage.local.set({
      [STORAGE_KEYS.CONNECTION_STATUS]: status,
      [STORAGE_KEYS.LAST_LATENCY_MS]: latencyMs
    });
  } catch (err) {
    logger.warn('Não foi possível gravar status de conexão no storage:', err);
  }
}

/**
 * Incrementa o total de comandos executados com sucesso nesta sessão.
 * @returns {Promise<number>} Total atualizado de comandos.
 */
export async function incrementCommandCount() {
  try {
    const data = await chrome.storage.local.get(STORAGE_KEYS.TOTAL_COMMANDS);
    const count = (data[STORAGE_KEYS.TOTAL_COMMANDS] || 0) + 1;
    await chrome.storage.local.set({ [STORAGE_KEYS.TOTAL_COMMANDS]: count });
    return count;
  } catch (err) {
    return 0;
  }
}

/**
 * Registra a autorização do módulo Computer Use recebida do Desktop App.
 * @param {boolean} allowed - Se o controle do computador está liberado.
 */
export async function setComputerUseAllowed(allowed) {
  try {
    await chrome.storage.local.set({ [STORAGE_KEYS.COMPUTER_USE_ALLOWED]: !!allowed });
  } catch (err) {
    logger.warn('Erro ao atualizar permissão de Computer Use:', err);
  }
}
