/**
 * @file screenshot_capture.js
 * @description Módulo de captura visual de abas da extensão Browser MTS.
 * 
 * Captura a imagem da viewport da aba ativa em formato base64 com tratamento
 * preventivo para abas restritas do navegador ou janelas sem foco.
 */

import { logger } from '../common/logger.js';
import { getActiveTab } from './tab_manager.js';

/**
 * Captura o conteúdo visual da aba ativa atual.
 * 
 * @param {string} [format='png'] - Formato da imagem ('png' ou 'jpeg').
 * @param {number} [quality=90] - Qualidade da imagem para formato JPEG (1-100).
 * @returns {Promise<object>} Objeto contendo string base64 e metadados da imagem.
 */
export async function captureTabScreenshot(format = 'png', quality = 90) {
  const activeTab = await getActiveTab();
  if (!activeTab || !activeTab.id) {
    throw new Error('Nenhuma aba ativa localizada para captura de tela.');
  }

  // Prevenção: URLs restritas do Chromium impedem captura de tela
  const url = activeTab.url || '';
  if (url.startsWith('chrome://') || url.startsWith('edge://') || url.startsWith('chrome-extension://')) {
    throw new Error(`Captura não permitida pelo navegador em URLs internas do sistema (${url}).`);
  }

  const captureOptions = {
    format: format === 'jpeg' ? 'jpeg' : 'png'
  };

  if (captureOptions.format === 'jpeg') {
    captureOptions.quality = Math.max(1, Math.min(100, quality));
  }

  try {
    const dataUrl = await chrome.tabs.captureVisibleTab(activeTab.windowId, captureOptions);
    if (!dataUrl) {
      throw new Error('O navegador não retornou dados visuais para a aba informada.');
    }

    const [header, base64Data] = dataUrl.split(',');
    const mimeType = header.match(/:(.*?);/)?.[1] || `image/${captureOptions.format}`;

    logger.info(`Captura de tela realizada na aba ID ${activeTab.id} (${mimeType}).`);

    return {
      success: true,
      base64: base64Data,
      dataUrl,
      mimeType,
      tabId: activeTab.id,
      tabTitle: activeTab.title || '',
      url: activeTab.url || ''
    };
  } catch (err) {
    logger.error('Falha ao capturar aba visual:', err);
    throw new Error(`Erro na captura da aba: ${err.message}`);
  }
}
