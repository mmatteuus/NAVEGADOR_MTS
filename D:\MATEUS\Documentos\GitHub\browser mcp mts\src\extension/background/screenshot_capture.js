/**
 * @file screenshot_capture.js
 * @description Módulo de captura visual de abas com suporte a CDP em background e fallback nativo.
 * Captura imagens em base64 da viewport por tabId sem exigir que a aba esteja em primeiro plano.
 */

import { logger } from '../common/logger.js';
import { getActiveTab } from './tab_manager.js';
import { cdpCaptureScreenshot } from './cdp_actions.js';

/**
 * Valida se uma URL pertence ao sistema interno protegido do navegador.
 * @param {string} url - URL a ser verificada.
 */
function validateUrlAccess(url) {
  const targetUrl = url || '';
  if (targetUrl.startsWith('chrome://') || targetUrl.startsWith('edge://') || targetUrl.startsWith('chrome-extension://')) {
    throw new Error(`Captura não permitida pelo navegador em URLs internas do sistema (${targetUrl}).`);
  }
}

/**
 * Captura o conteúdo visual de uma aba especificada (ou da aba ativa).
 * @param {string} [format='png'] - Formato da imagem ('png' ou 'jpeg').
 * @param {number} [quality=90] - Qualidade para formato JPEG (1-100).
 * @param {number} [tabId=null] - ID opcional da aba para captura em background.
 */
export async function captureTabScreenshot(format = 'png', quality = 90, tabId = null) {
  let targetTab = null;

  if (tabId !== null && tabId !== undefined) {
    if (!Number.isInteger(tabId) || tabId <= 0) throw new Error('ID de aba inválido para captura.');
    try {
      if (chrome.tabs.get) targetTab = await chrome.tabs.get(tabId);
    } catch (_err) {
      targetTab = null;
    }
    if (!targetTab) {
      const tabs = await chrome.tabs.query({});
      targetTab = tabs.find(t => t.id === tabId);
    }
    if (!targetTab) throw new Error('A aba informada não está disponível para captura.');
  }

  if (!targetTab) {
    targetTab = await getActiveTab();
  }

  if (!targetTab || !targetTab.id) {
    throw new Error('Nenhuma aba válida localizada para captura de tela.');
  }

  validateUrlAccess(targetTab.url);

  // Tentativa primária: CDP em background (não rouba foco e funciona em abas ocultas)
  try {
    const cdpResult = await cdpCaptureScreenshot(targetTab.id, format, quality);
    return {
      success: true,
      base64: cdpResult.base64,
      dataUrl: cdpResult.dataUrl,
      mimeType: cdpResult.mimeType,
      tabId: targetTab.id,
      tabTitle: targetTab.title || '',
      url: targetTab.url || ''
    };
  } catch (cdpErr) {
    logger.warn(`Captura via CDP falhou na aba ID ${targetTab.id} (${cdpErr.message}). Tentando fallback...`);
  }

  // Fallback suave: captureVisibleTab caso seja a aba ativa
  const activeTabs = await chrome.tabs.query({ active: true, windowId: targetTab.windowId });
  if (!activeTabs.some(tab => tab.id === targetTab.id)) {
    throw new Error('Captura fallback recusada: a aba alvo não está ativa.');
  }
  const captureOptions = { format: format === 'jpeg' ? 'jpeg' : 'png' };
  if (captureOptions.format === 'jpeg') {
    captureOptions.quality = Math.max(1, Math.min(100, quality));
  }

  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(targetTab.windowId, captureOptions);
    if (!dataUrl) throw new Error('O navegador não retornou dados visuais para a aba informada.');

    const [header, base64Data] = dataUrl.split(',');
    const mimeType = header.match(/:(.*?);/)?.[1] || `image/${captureOptions.format}`;
    logger.info(`Captura realizada via fallback na aba ID ${targetTab.id} (${mimeType}).`);

    return {
      success: true,
      base64: base64Data,
      dataUrl,
      mimeType,
      tabId: targetTab.id,
      tabTitle: targetTab.title || '',
      url: targetTab.url || ''
    };
  } catch (err) {
    logger.error('Falha geral ao capturar aba visual:', err);
    throw new Error(`Erro na captura da aba: ${err.message}`);
  }
}
