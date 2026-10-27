/**
 * @file content_bridge.js
 * @description Ponte de comunicação entre o Service Worker e os submódulos de página.
 * Escuta requisições via chrome.tabs.sendMessage, aciona os módulos correspondentes
 * e mantém o cursor virtual do agente sincronizado no DOM.
 */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  const previous = window.__BrowserMTS__.__contentBridge;
  if (previous?.listener) {
    try { chrome.runtime.onMessage.removeListener(previous.listener); } catch (_) {}
  }
  const listener = (message, _sender, sendResponse) => {
    if (window.__BrowserMTS__.__contentBridge?.listener !== listener) return false;
    const { action, params = {} } = message;
    handleAction(action, params)
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message || String(err) }));
    return true; // Mantém canal aberto para resposta assíncrona
  };
  window.__BrowserMTS__.__contentBridge = { listener, runtimeId: chrome.runtime.id || '' };
  chrome.runtime.onMessage.addListener(listener);

  /**
   * Encaminha o comando recebido para a função correspondente.
   * @param {string} action - Nome da ação solicitada.
   * @param {object} params - Parâmetros da ação.
   */
  async function handleAction(action, params) {
    const modules = window.__BrowserMTS__;

    switch (action) {
      case 'browser_click': {
        const res = await modules.interaction.clickElement(params);
        if (modules.virtualCursor && res?.coordinates) {
          modules.virtualCursor.showClick(res.coordinates.x, res.coordinates.y, params.button || 'left');
        }
        return res;
      }

      case 'browser_type':
        return modules.interaction.typeText(params);

      case 'browser_hover': {
        const res = await modules.interaction.hoverElement(params);
        if (modules.virtualCursor && typeof params.x === 'number' && typeof params.y === 'number') {
          modules.virtualCursor.updatePosition(params.x, params.y, true);
        }
        return res;
      }

      case 'browser_drag':
        return modules.dragSimulator.simulateDrag(params);

      case 'browser_mouse_action': {
        const act = params.action || 'move';
        const vCursor = modules.virtualCursor;
        if (act === 'move' && vCursor) {
          return { success: true, position: vCursor.updatePosition(params.x || 0, params.y || 0, params.smooth !== false) };
        }
        if ((act === 'click' || act === 'double_click' || act === 'right_click') && vCursor) {
          return { success: true, click: vCursor.showClick(params.x || 0, params.y || 0, params.button || 'left') };
        }
        if (act === 'drag' && modules.dragSimulator) {
          return modules.dragSimulator.simulateDrag(params);
        }
        return { success: true, action: act };
      }

      case 'browser_select':
      case 'browser_select_option':
        return modules.interaction.selectOption(params);

      case 'browser_press_key':
        return modules.keyboardScroll.pressKey(params);

      case 'browser_scroll':
        return modules.keyboardScroll.scrollPage(params);

      case 'browser_get_dom':
        return modules.domExtractor.extractCleanDOM(params.clean, params.maxDepth);

      case 'browser_get_text':
        return modules.domExtractor.extractPageText(params.selector);

      case 'browser_snapshot':
        return modules.domExtractor.extractAriaSnapshot();

      case 'browser_find_elements':
        return modules.elementFinder.findMultipleElements(params.selector, params.visibleOnly);

      case 'browser_evaluate_js':
        return modules.evalRunner.evaluateScript(params.script);

      default:
        throw new Error(`Ação de content script não suportada: '${action}'.`);
    }
  }
})();
