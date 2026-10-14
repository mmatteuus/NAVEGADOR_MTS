/**
 * @file element_finder.js
 * @description Localizador resiliente de elementos no DOM para automação por IA.
 * 
 * Fornece busca por seletores CSS, texto visível e referências semânticas,
 * calculando coordenadas reais com verificação de visibilidade e suporte a SPAs.
 */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  /**
   * Determina se um nó do DOM está visível na viewport do usuário.
   * @param {Element} el - Nó HTML a verificar.
   * @returns {boolean} Verdadeiro se o elemento tiver área e visibilidade ativa.
   */
  function isElementVisible(el) {
    if (!el || !(el instanceof Element)) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
      return false;
    }
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  /**
   * Localiza um único elemento no documento com tentativa resiliente.
   * @param {object} params - Critérios de busca (selector, ref, x, y).
   * @returns {Promise<Element>} Elemento encontrado ou rejeição com erro.
   */
  async function findTargetElement(params) {
    const { selector, ref, x, y } = params;

    // 1. Busca por coordenadas diretas se fornecidas
    if (typeof x === 'number' && typeof y === 'number') {
      const elAtPoint = document.elementFromPoint(x, y);
      if (elAtPoint) return elAtPoint;
    }

    // 2. Busca por referência interna de snapshot ou atributo data-ref
    if (ref) {
      const byRef = document.querySelector(`[data-mcp-ref="${ref}"], [data-ref="${ref}"]`);
      if (byRef) return byRef;
    }

    // 3. Busca por seletor CSS com tolerância e retry para SPAs
    if (selector) {
      let el = document.querySelector(selector);
      if (el) return el;

      // Espera preventiva curta para elementos renderizados dinamicamente
      await new Promise(res => setTimeout(res, 150));
      el = document.querySelector(selector);
      if (el) return el;
    }

    throw new Error(`Elemento não encontrado no DOM (Seletor: '${selector || 'N/A'}', Ref: '${ref || 'N/A'}').`);
  }

  /**
   * Localiza múltiplos elementos para a ferramenta browser_find_elements.
   * @param {string} selector - Seletor CSS a pesquisar.
   * @param {boolean} [visibleOnly=true] - Filtrar apenas nós visíveis.
   * @returns {Array<object>} Relação de elementos com coordenadas e textos.
   */
  function findMultipleElements(selector, visibleOnly = true) {
    const nodeList = document.querySelectorAll(selector || '*');
    const results = [];

    let index = 0;
    for (const node of nodeList) {
      if (visibleOnly && !isElementVisible(node)) continue;
      const rect = node.getBoundingClientRect();

      results.push({
        index: index++,
        tagName: node.tagName.toLowerCase(),
        id: node.id || '',
        className: node.className || '',
        text: (node.textContent || '').trim().slice(0, 100),
        bounds: {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height)
        },
        isVisible: true
      });

      if (results.length >= 50) break; // Limite defensivo para evitar payload excessivo
    }

    return results;
  }

  /**
   * Retorna os limites e o centroide de um elemento.
   * @param {Element} el - Nó HTML.
   * @returns {object} Coordenadas x, y centrais e dimensões.
   */
  function getElementBounds(el) {
    const rect = el.getBoundingClientRect();
    return {
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
      centerX: Math.round(rect.x + rect.width / 2),
      centerY: Math.round(rect.y + rect.height / 2)
    };
  }

  window.__BrowserMTS__.elementFinder = {
    isElementVisible,
    findTargetElement,
    findMultipleElements,
    getElementBounds
  };
})();
