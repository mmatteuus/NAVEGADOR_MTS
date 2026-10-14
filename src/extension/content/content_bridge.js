/**
 * @file content_bridge.js
 * @description Ponte de comunicação entre o Service Worker e os submódulos de página.
 * 
 * Escuta requisições encaminhadas via chrome.tabs.sendMessage, aciona os módulos
 * de inspeção/interação correspondentes e devolve respostas assíncronas ao worker.
 */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    const { action, params = {} } = message;

    handleAction(action, params)
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message || String(err) }));

    return true; // Mantém canal aberto para resposta assíncrona
  });

  /**
   * Encaminha o comando recebido para a função correspondente.
   * @param {string} action - Nome da ação solicitada.
   * @param {object} params - Parâmetros da ação.
   * @returns {Promise<any>} Resultado da operação.
   */
  async function handleAction(action, params) {
    const modules = window.__BrowserMTS__;

    switch (action) {
      case 'browser_click':
        return modules.interaction.clickElement(params);

      case 'browser_type':
        return modules.interaction.typeText(params);

      case 'browser_hover':
        return modules.interaction.hoverElement(params);

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

  console.log('[BrowserMTS] Content script carregado e pronto para comandos.');
})();
