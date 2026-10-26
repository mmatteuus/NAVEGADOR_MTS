/**
 * @file dom_extractor.js
 * @description Extrator semântico do DOM e árvore de acessibilidade para agentes de IA.
 * 
 * Limpa elementos de ruído (scripts, estilos, SVGs pesados), compacta hierarquias
 * e entrega um resumo conciso do conteúdo para consumo eficiente de tokens pelo LLM.
 */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  const IGNORED_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'PATH', 'TEMPLATE', 'IFRAME']);
  const MAX_VISIBLE_TEXT = 20000;
  // Cache de indentação para otimização de travessia do DOM
  const INDENT_CACHE = Array.from({ length: 30 }, (_, i) => '  '.repeat(i));

  function getIndent(depth) {
    return INDENT_CACHE[depth] || '  '.repeat(depth);
  }

  /**
   * Extrai e formata a árvore do DOM de forma simplificada e indentada.
   * @param {boolean} [clean=true] - Se deve filtrar ruídos e espaços vazios.
   * @param {number} [maxDepth=10] - Limite máximo de profundidade na árvore.
   * @returns {object} Árvore textual do DOM, total de nós e metadados.
   */
  function extractCleanDOM(clean = true, maxDepth = 10) {
    let nodeCount = 0;

    function traverse(node, depth) {
      if (!node || depth > maxDepth) return '';
      const indent = getIndent(depth);
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent.trim();
        return text ? `${indent}"${text}"\n` : '';
      }

      if (node.nodeType !== Node.ELEMENT_NODE) return '';
      if (clean && IGNORED_TAGS.has(node.tagName)) return '';

      nodeCount++;
      const tag = node.tagName.toLowerCase();
      let meta = tag;

      if (node.id) meta += `#${node.id}`;
      if (node.className && typeof node.className === 'string') {
        const spaceIdx = node.className.indexOf(' ');
        const firstClass = spaceIdx === -1 ? node.className : node.className.slice(0, spaceIdx);
        if (firstClass) meta += `.${firstClass}`;
      }
      const role = node.getAttribute('role');
      if (role) meta += ` [role="${role}"]`;
      const ariaLabel = node.getAttribute('aria-label');
      if (ariaLabel) meta += ` [label="${ariaLabel}"]`;

      let output = `${indent}<${meta}>\n`;
      const children = node.childNodes;
      for (let i = 0; i < children.length; i++) {
        output += traverse(children[i], depth + 1);
      }
      return output;
    }

    const tree = traverse(document.body || document.documentElement, 0);
    return {
      success: true,
      dom: tree,
      totalNodes: nodeCount,
      url: window.location.href,
      title: document.title
    };
  }

  /**
   * Extrai todo o texto legível da página ou do container especificado.
   * @param {string} [selector] - Seletor CSS opcional do container.
   * @returns {object} Texto concatenado e contagem de caracteres.
   */
  function extractPageText(selector) {
    const root = selector ? document.querySelector(selector) : (document.body || document.documentElement);
    if (!root) throw new Error(`Container não encontrado para extração de texto: '${selector}'`);

    const rawText = root.innerText || root.textContent || '';
    const cleanText = rawText.replace(/\s+/g, ' ').trim();

    return {
      success: true,
      text: cleanText,
      characterCount: cleanText.length,
      url: window.location.href
    };
  }

  /**
   * Cria um snapshot semântico focado em elementos acionáveis (botões, links, inputs).
   * @returns {object} Snapshot semântico com referências e títulos.
   */
  function extractAriaSnapshot() {
    const interactives = document.querySelectorAll('button, a, input, select, textarea, [role="button"], [role="link"]');
    const snapshotLines = [];

    interactives.forEach((el, idx) => {
      if (el.offsetParent === null) return; // Ignora elementos ocultos
      const refId = `ref_${idx + 1}`;
      el.setAttribute('data-mcp-ref', refId);

      const tag = el.tagName.toLowerCase();
      const isPassword = tag === 'input' && (el.type || '').toLowerCase() === 'password';
      const label = el.getAttribute('aria-label') || el.innerText || el.placeholder || (isPassword ? '' : el.value) || '';
      snapshotLines.push(`- ${tag} "${label.trim().slice(0, 60)}" [ref=${refId}]`);
    });

    const root = document.body || document.documentElement;
    const rawVisibleText = root && typeof root.innerText === 'string' ? root.innerText : '';
    const normalizedText = rawVisibleText.replace(/\s+/g, ' ').trim();
    const visibleTextTruncated = normalizedText.length > MAX_VISIBLE_TEXT;
    const visibleText = visibleTextTruncated ? normalizedText.slice(0, MAX_VISIBLE_TEXT) : normalizedText;
    const textSection = visibleText
      ? `\n\n[texto visível]\n${visibleText}${visibleTextTruncated ? '\n[texto visível truncado]' : ''}`
      : '';

    return {
      success: true,
      snapshot: snapshotLines.join('\n') + textSection,
      visibleText,
      visibleTextTruncated,
      totalInteractive: snapshotLines.length,
      url: window.location.href,
      title: document.title
    };
  }

  window.__BrowserMTS__.domExtractor = {
    extractCleanDOM,
    extractPageText,
    extractAriaSnapshot
  };
})();
