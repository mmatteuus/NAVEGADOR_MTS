/**
 * @file state_storage.js
 * @description Gerenciamento de persistência de estado local da extensão.
 *
 * Utiliza a API chrome.storage.local para reter preferências do usuário,
 * status de conexão, latência recente e contadores operacionais entre recargas.
 */

import { STORAGE_KEYS, CONNECTION_STATE } from '../common/constants.js';
import { logger } from '../common/logger.js';

let automationState = true;
let automationBlocked = false;
let transition = Promise.resolve();
let transitionId = 0;
const SESSION_BLOCK_KEY = 'browser_mts_automation_blocked_session';

async function sessionBlock() {
  if (!chrome.storage.session?.get) return false;
  const data = await chrome.storage.session.get(SESSION_BLOCK_KEY);
  return data?.[SESSION_BLOCK_KEY] === true;
}
async function setSessionBlock(blocked) {
  if (!chrome.storage.session?.set) return;
  await chrome.storage.session.set({ [SESSION_BLOCK_KEY]: !!blocked });
}
function enqueue(operation) {
  const result = transition.then(operation, operation);
  transition = result.catch(() => {});
  return result;
}

/**
 * Consulta se a automação web está autorizada pelo usuário.
 * @returns {Promise<boolean>} Verdadeiro se a chave estiver ligada (padrão true).
 */
export async function isAutomationEnabled() {
  const id = transitionId;
  return enqueue(async () => {
    if (automationBlocked || id !== transitionId) return false;
    try { if (await sessionBlock()) return false; }
    catch (err) { automationBlocked = true; automationState = false; return false; }
    try {
      const data = await chrome.storage.local.get(STORAGE_KEYS.AUTOMATION_ENABLED);
      if (id !== transitionId || automationBlocked) return false;
      automationState = data[STORAGE_KEYS.AUTOMATION_ENABLED] !== false;
      return automationState;
    } catch (err) {
      logger.error('Falha ao ler permissão de automação do storage:', err);
      automationState = false; return false;
    }
  });
}

/**
 * Atualiza o interruptor de automação (ligado/desligado) no storage.
 * @param {boolean} enabled - Novo estado do interruptor.
 */
export async function setAutomationEnabled(enabled) {
  const desired = !!enabled;
  const id = ++transitionId;
  if (!desired) { automationState = false; automationBlocked = true; }
  return enqueue(async () => {
    if (id !== transitionId) return automationState;
    try {
      if (!desired) {
        let failure = null;
        try { await setSessionBlock(true); } catch (err) { failure = err; }
        try { await chrome.storage.local.set({ [STORAGE_KEYS.AUTOMATION_ENABLED]: false }); }
        catch (err) { failure = failure || err; }
        if (failure) throw failure;
      } else {
        await chrome.storage.local.set({ [STORAGE_KEYS.AUTOMATION_ENABLED]: true });
        await setSessionBlock(false);
      }
      if (id !== transitionId) return automationState;
      automationState = desired; automationBlocked = !desired;
      logger.info(`Automação web ${desired ? 'HABILITADA' : 'DESABILITADA'} pelo usuário.`);
      return automationState;
    } catch (err) {
      logger.error('Erro ao persistir estado de automação:', err);
      automationState = false; automationBlocked = true;
      await setSessionBlock(true).catch(() => {});
      throw new Error('AUTOMATION_STATE_PERSIST_FAILED');
    }
  });
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
