/**
 * @file cdp_controller.js
 * @description Gerenciador resiliente de sessões Chrome DevTools Protocol (CDP) por aba.
 * Controla o ciclo de vida da API chrome.debugger, conexões e envio de comandos.
 */

import { logger } from '../common/logger.js';

const attachedTabs = new Set();

// Escuta desanexações espontâneas do navegador (ex: aba fechada ou DevTools manual)
if (typeof chrome !== 'undefined' && chrome.debugger?.onDetach) {
  chrome.debugger.onDetach.addListener((source, reason) => {
    if (source && source.tabId) {
      attachedTabs.delete(source.tabId);
      logger.info(`Sessão CDP desanexada da aba ID ${source.tabId} (${reason || 'desconhecido'}).`);
    }
  });
}

/**
 * Conecta a sessão do depurador CDP na aba indicada.
 * @param {number} tabId - ID da aba alvo.
 * @param {string} [version='1.3'] - Versão do protocolo CDP.
 * @returns {Promise<boolean>} Confirmação de conexão.
 */
export async function attachTab(tabId, version = '1.3') {
  if (!tabId || typeof tabId !== 'number') {
    throw new Error('ID de aba inválido para anexação de sessão CDP.');
  }
  if (attachedTabs.has(tabId)) return true;
  if (!chrome.debugger || !chrome.debugger.attach) {
    throw new Error('API chrome.debugger não está disponível neste ambiente.');
  }

  try {
    await chrome.debugger.attach({ tabId }, version);
    attachedTabs.add(tabId);
    logger.info(`Sessão CDP anexada com sucesso na aba ID ${tabId} (v${version}).`);
    return true;
  } catch (err) {
    if (err.message && err.message.includes('already attached')) {
      attachedTabs.add(tabId);
      return true;
    }
    logger.error(`Falha ao anexar sessão CDP na aba ID ${tabId}:`, err.message);
    throw err;
  }
}

/**
 * Desconecta a sessão do depurador CDP da aba.
 * @param {number} tabId - ID da aba a ser desanexada.
 */
export async function detachTab(tabId) {
  if (!attachedTabs.has(tabId)) return false;
  try {
    await chrome.debugger.detach({ tabId });
    attachedTabs.delete(tabId);
    logger.info(`Sessão CDP desanexada da aba ID ${tabId}.`);
    return true;
  } catch (err) {
    attachedTabs.delete(tabId);
    logger.warn(`Aviso ao desanexar CDP da aba ID ${tabId}:`, err.message);
    return false;
  }
}

/**
 * Envia um comando CDP para a aba com auto-anexação preventiva.
 * @param {number} tabId - ID da aba alvo.
 * @param {string} method - Método CDP (ex: 'Page.captureScreenshot').
 * @param {object} [params={}] - Parâmetros do comando CDP.
 * @returns {Promise<any>} Resposta do motor Blink.
 */
export async function sendCdpCommand(tabId, method, params = {}) {
  await attachTab(tabId);
  try {
    return await chrome.debugger.sendCommand({ tabId }, method, params);
  } catch (err) {
    logger.error(`Erro no comando CDP '${method}' na aba ${tabId}:`, err.message);
    throw err;
  }
}

/** Verifica se a aba está com sessão CDP ativa. */
export function isTabAttached(tabId) {
  return attachedTabs.has(tabId);
}

/** Desconecta todas as sessões CDP ativas. */
export async function detachAllTabs() {
  const promises = Array.from(attachedTabs).map(tabId => detachTab(tabId));
  await Promise.allSettled(promises);
}
