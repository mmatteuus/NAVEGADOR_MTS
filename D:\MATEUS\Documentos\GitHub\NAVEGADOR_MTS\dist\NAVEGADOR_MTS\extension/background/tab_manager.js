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
 * @param {boolean} [active=false] - Se a aba deve receber foco (padrão: falso).
 * @returns {Promise<object>} Detalhes da navegação concluída.
 */
export async function navigate(url, tabId, active = false) {
  if (tabId != null && (!Number.isInteger(tabId) || tabId <= 0)) throw new Error('TAB_ID_INVALID');
  let targetTabId = tabId;
  if (targetTabId == null) {
    const activeTab = await getActiveTab();
    if (!activeTab || !activeTab.id) {
      const created = await chrome.tabs.create({ url, active: active });
      return { success: true, url, tabId: created.id, title: created.title || '' };
    }
    targetTabId = activeTab.id;
  }

  const updated = await chrome.tabs.update(targetTabId, { url, active: active });
  logger.info(`Navegação iniciada para '${url}' na aba ID ${targetTabId} (Ativar: ${active}).`);
  return { success: true, url, tabId: targetTabId, title: updated.title || '' };
}

/**
 * Abre uma nova aba no navegador.
 * @param {string} [url='about:blank'] - Endereço a carregar.
 * @param {boolean} [active=true] - Se a nova aba deve receber foco imediato.
 * @returns {Promise<object>} Identificador e URL da aba criada.
 */
export async function newTab(url = 'about:blank', active = false) {
  const tab = await chrome.tabs.create({ url, active });
  logger.info(`Nova aba criada (ID: ${tab.id}, Ativa: ${active}).`);
  return { success: true, tabId: tab.id, url: tab.url || url, active: tab.active ?? active };
}

/**
 * Fecha a aba informada com proteção contra fechamento da janela.
 * @param {number} [tabId] - ID da aba a fechar (ou ativa).
 * @returns {Promise<object>} Confirmação de fechamento.
 */
export async function closeTab(tabId) {
  if (tabId != null && (!Number.isInteger(tabId) || tabId <= 0)) throw new Error('TAB_ID_INVALID');
  const allTabs = await chrome.tabs.query({ currentWindow: true });
  let targetId = tabId;

  if (targetId == null) {
    const active = await getActiveTab();
    targetId = active?.id;
  }

  if (targetId == null) throw new Error('Nenhuma aba disponível para fechar.');

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
 * @param {boolean} [bringWindowToFront=false] - Se deve trazer a janela do navegador para frente.
 * @returns {Promise<object>} Confirmação da aba ativada.
 */
export async function switchTab(tabId, bringWindowToFront = false) {
  const tab = await chrome.tabs.update(tabId, { active: true });
  if (bringWindowToFront && tab.windowId) {
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
  if (tabId != null && (!Number.isInteger(tabId) || tabId <= 0)) throw new Error('TAB_ID_INVALID');
  const active = tabId == null ? await getActiveTab() : { id: tabId };
  if (!active?.id) throw new Error('Nenhuma aba disponível.');
  await chrome.tabs.goBack(active.id);
  return { success: true, action: 'go_back', tabId: active.id };
}

/**
 * Avança no histórico da aba.
 * @param {number} [tabId] - ID da aba alvo.
 */
export async function goForward(tabId) {
  if (tabId != null && (!Number.isInteger(tabId) || tabId <= 0)) throw new Error('TAB_ID_INVALID');
  const active = tabId == null ? await getActiveTab() : { id: tabId };
  if (!active?.id) throw new Error('Nenhuma aba disponível.');
  await chrome.tabs.goForward(active.id);
  return { success: true, action: 'go_forward', tabId: active.id };
}
