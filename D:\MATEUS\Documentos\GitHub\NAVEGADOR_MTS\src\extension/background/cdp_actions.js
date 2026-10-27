/**
 * @file cdp_actions.js
 * @description Ações avançadas via Chrome DevTools Protocol (CDP) em abas em segundo plano.
 * Permite captura de tela isolada por tabId e despacho de eventos nativos de mouse e teclado.
 */

import { logger } from '../common/logger.js';
import { sendCdpCommand } from './cdp_controller.js';

/**
 * Captura screenshot de qualquer aba em background via CDP sem roubar foco da janela.
 * @param {number} tabId - ID da aba alvo.
 * @param {string} [format='png'] - Formato da imagem ('png' ou 'jpeg').
 * @param {number} [quality=90] - Qualidade (1-100 para jpeg).
 */
export async function cdpCaptureScreenshot(tabId, format = 'png', quality = 90) {
  if (!tabId || typeof tabId !== 'number') {
    throw new Error('ID de aba obrigatório para captura de tela via CDP.');
  }

  const fmt = format === 'jpeg' ? 'jpeg' : 'png';
  const cdpParams = { format: fmt };
  if (fmt === 'jpeg') cdpParams.quality = Math.max(1, Math.min(100, quality));

  await sendCdpCommand(tabId, 'Page.enable');
  const res = await sendCdpCommand(tabId, 'Page.captureScreenshot', cdpParams);

  if (!res || !res.data) {
    throw new Error('CDP Page.captureScreenshot não retornou dados de imagem.');
  }

  const mimeType = `image/${fmt}`;
  logger.info(`Captura de tela via CDP na aba ID ${tabId} concluída com sucesso.`);
  return {
    success: true,
    base64: res.data,
    dataUrl: `data:${mimeType};base64,${res.data}`,
    mimeType,
    tabId
  };
}

/**
 * Despacha evento de mouse nativo de alta fidelidade (isTrusted) via CDP.
 * @param {number} tabId - ID da aba.
 * @param {object} params - { type, x, y, button, clickCount, deltaX, deltaY }
 */
export async function cdpDispatchMouse(tabId, params = {}) {
  const { type = 'mouseMoved', x = 0, y = 0, button = 'none', clickCount = 1, deltaX = 0, deltaY = 0 } = params;
  const cdpParams = { type, x, y, button, clickCount, deltaX, deltaY };
  await sendCdpCommand(tabId, 'Input.dispatchMouseEvent', cdpParams);
  return { success: true, tabId, x, y, type };
}

/**
 * Despacha evento de teclado nativo de alta fidelidade (isTrusted) via CDP.
 * @param {number} tabId - ID da aba.
 * @param {object} params - { type, text, key, code, windowsVirtualKeyCode }
 */
export async function cdpDispatchKey(tabId, params = {}) {
  const { type = 'keyDown', text = '', key = '', code = '', windowsVirtualKeyCode = 0 } = params;
  const cdpParams = { type, text, key, code, windowsVirtualKeyCode };
  await sendCdpCommand(tabId, 'Input.dispatchKeyEvent', cdpParams);
  return { success: true, tabId, key: key || text, type };
}

/**
 * Executa sequência coordenada de arrasto (drag & drop) de alta fidelidade via CDP.
 * @param {number} tabId - ID da aba.
 * @param {object} params - { startX, startY, endX, endY, steps }
 */
export async function cdpDispatchDrag(tabId, params = {}) {
  const { startX = 0, startY = 0, endX = 0, endY = 0, steps = 5 } = params;
  await cdpDispatchMouse(tabId, { type: 'mouseMoved', x: startX, y: startY });
  await cdpDispatchMouse(tabId, { type: 'mousePressed', x: startX, y: startY, button: 'left', clickCount: 1 });

  const numSteps = Math.max(1, steps);
  for (let i = 1; i <= numSteps; i++) {
    const curX = Math.round(startX + ((endX - startX) * i) / numSteps);
    const curY = Math.round(startY + ((endY - startY) * i) / numSteps);
    await cdpDispatchMouse(tabId, { type: 'mouseMoved', x: curX, y: curY, button: 'left' });
  }

  await cdpDispatchMouse(tabId, { type: 'mouseReleased', x: endX, y: endY, button: 'left', clickCount: 1 });
  logger.info(`Arrasto via CDP concluído na aba ID ${tabId} de (${startX}, ${startY}) até (${endX}, ${endY}).`);
  return { success: true, tabId, from: { x: startX, y: startY }, to: { x: endX, y: endY } };
}
