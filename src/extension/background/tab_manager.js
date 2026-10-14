/**
 * @file tab_manager.js
 * @description Gerenciamento resiliente de abas e navegação via API chrome.tabs.
 * 
 * Contém prevenção de falhas em cascata, como evitar fechar a janela do Chrome
 * quando o agente solicita fechar a única aba restante aberta.
 */

import { logger } from '../common/logger.js';

/**
 * Obtém a aba atualmente ativa na janela com foco.
 * @returns {Promise<chrome.tabs.Tab|null>} Aba ativa ou null.
 */
export async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs.length > 0 ? tabs[0] : null;
}

/**
 * Navega para uma URL específica e aguarda a conclusão da carga.
 * @param {string} url - Endereço de destino.
 * @param {number} [tabId] - ID da aba alvo (se omitido usa a aba ativa).
 * @returns {Promise<object>} Detalhes da navegação concluída.
 */
export async function navigate(url, tabId) {
  let targetTabId = tabId;
  if (!targetTabId) {
    const active = await getActiveTab();
    if (!active || !active.id) {
      const created = await chrome.tabs.create({ url, active: true });
      return { success: true, url, tabId: created.id, title: created.title || '' };
    }
    targetTabId = active.id;
  }

  const updated = await chrome.tabs.update(targetTabId, { url });
  logger.info(`Navegação iniciada para '${url}' na aba ID ${targetTabId}.`);
  return { success: true, url, tabId: targetTabId, title: updated.title || '' };
}

/**
 * Abre uma nova aba no navegador.
 * @param {string} [url='about:blank'] - Endereço a carregar.
 * @param {boolean} [active=true] - Se a nova aba deve receber foco imediato.
 * @returns {Promise<object>} Identificador e URL da aba criada.
 */
export async function newTab(url = 'about:blank', active = true) {
  const tab = await chrome.tabs.create({ url, active });
  logger.info(`Nova aba criada (ID: ${tab.id}, Ativa: ${active}).`);
  return { success: true, tabId: tab.id, url: tab.url || url };
}

/**
 * Fecha a aba informada com proteção contra fechamento da janela.
 * @param {number} [tabId] - ID da aba a fechar (ou ativa).
 * @returns {Promise<object>} Confirmação de fechamento.
 */
export async function closeTab(tabId) {
  const allTabs = await chrome.tabs.query({ currentWindow: true });
  let targetId = tabId;

  if (!targetId) {
    const active = await getActiveTab();
    targetId = active?.id;
  }

  if (!targetId) throw new Error('Nenhuma aba disponível para fechar.');

  // Prevenção: se for a única aba aberta, abre uma aba neutra antes
  if (allTabs.length <= 1) {
    logger.warn('Última aba restante sendo fechada. Abrindo about:blank preventiva.');
    await chrome.tabs.create({ url: 'about:blank', active: true });
  }

  await chrome.tabs.remove(targetId);
  logger.info(`Aba ID ${targetId} fechada com sucesso.`);
  return { success: true, closedTabId: targetId };
}

/**
 * Alterna o foco para a aba solicitada.
 * @param {number} tabId - ID da aba a ativar.
 * @returns {Promise<object>} Confirmação da aba ativada.
 */
export async function switchTab(tabId) {
  const tab = await chrome.tabs.update(tabId, { active: true });
  if (tab.windowId) {
    await chrome.windows.update(tab.windowId, { focused: true });
  }
  return { success: true, activeTabId: tabId, title: tab.title || '', url: tab.url || '' };
}

/**
 * Lista todas as abas abertas no navegador.
 * @param {boolean} [currentWindowOnly=true] - Filtrar apenas janela atual.
 * @returns {Promise<Array<object>>} Relação de abas com metadados.
 */
export async function listTabs(currentWindowOnly = true) {
  const query = currentWindowOnly ? { currentWindow: true } : {};
  const tabs = await chrome.tabs.query(query);
  return tabs.map(t => ({
    id: t.id,
    index: t.index,
    title: t.title || '',
    url: t.url || '',
    active: !!t.active,
    favIconUrl: t.favIconUrl || ''
  }));
}

/**
 * Navega de volta no histórico da aba.
 * @param {number} [tabId] - ID da aba alvo.
 */
export async function goBack(tabId) {
  const active = tabId ? { id: tabId } : await getActiveTab();
  await chrome.tabs.goBack(active.id);
  return { success: true, action: 'go_back', tabId: active.id };
}

/**
 * Avança no histórico da aba.
 * @param {number} [tabId] - ID da aba alvo.
 */
export async function goForward(tabId) {
  const active = tabId ? { id: tabId } : await getActiveTab();
  await chrome.tabs.goForward(active.id);
  return { success: true, action: 'go_forward', tabId: active.id };
}
