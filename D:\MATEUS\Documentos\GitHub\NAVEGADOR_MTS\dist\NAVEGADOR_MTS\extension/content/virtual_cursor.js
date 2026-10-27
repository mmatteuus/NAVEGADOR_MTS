/**
 * @file virtual_cursor.js
 * @description Cursor virtual exclusivo do agente de IA renderizado no DOM da aba.
 * Permite visualizar movimentos, cliques e arrastos do agente sem interferir no cursor físico.
 */
window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  let cursorEl = null, focusedEl = null, currentPos = { x: 0, y: 0 };
  const CURSOR_ID = 'browser-mts-virtual-cursor', STYLES_ID = 'browser-mts-cursor-styles';

  /** Injeta estilos e elementos visuais do cursor virtual no DOM. */
  function ensureDOM() {
    if (document.getElementById(CURSOR_ID) && cursorEl) return;
    if (!document.getElementById(STYLES_ID)) {
      const style = document.createElement('style');
      style.id = STYLES_ID;
      style.textContent = `
        #${CURSOR_ID} { position: fixed; top: 0; left: 0; width: 22px; height: 22px;
          z-index: 2147483647; pointer-events: none !important;
          transition: transform 0.12s cubic-bezier(0.2, 0.8, 0.2, 1);
          transform: translate3d(0, 0, 0); will-change: transform; }
        .mts-cursor-ripple { position: fixed; border-radius: 50%; pointer-events: none !important;
          z-index: 2147483646; transform: translate(-50%, -50%) scale(0.2);
          animation: mts-ripple-anim 0.35s ease-out forwards; }
        .mts-drag-trail { position: fixed; pointer-events: none !important; z-index: 2147483645;
          stroke: #8a2be2; stroke-width: 2.5; stroke-dasharray: 4 3; opacity: 0.85; }
        .mts-virtual-focus { outline: 2px dashed #8a2be2 !important; outline-offset: 2px !important; }
        @keyframes mts-ripple-anim { to { transform: translate(-50%, -50%) scale(1.6); opacity: 0; } }
      `;
      (document.head || document.documentElement).appendChild(style);
    }
    cursorEl = document.createElement('div');
    cursorEl.id = CURSOR_ID;
    cursorEl.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M4 3L19 12L12 14L8 21L4 3Z" fill="#8a2be2" stroke="#ffffff" stroke-width="1.8"/>
      <circle cx="15" cy="15" r="4.5" fill="#00e5ff" stroke="#ffffff" stroke-width="1.2"/>
    </svg>`;
    (document.body || document.documentElement).appendChild(cursorEl);
  }

  /** Atualiza a posição (x, y) do cursor virtual com transição opcional. */
  function updatePosition(x, y, smooth = true) {
    ensureDOM();
    currentPos = { x, y };
    if (!cursorEl) return currentPos;
    cursorEl.style.transition = smooth ? 'transform 0.12s cubic-bezier(0.2, 0.8, 0.2, 1)' : 'none';
    cursorEl.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    return currentPos;
  }

  /** Renderiza ondulação animada de clique nas coordenadas especificadas. */
  function showClick(x, y, button = 'left') {
    ensureDOM();
    updatePosition(x, y, false);
    const ripple = document.createElement('div');
    ripple.className = 'mts-cursor-ripple';
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    ripple.style.width = '28px';
    ripple.style.height = '28px';
    ripple.style.backgroundColor = button === 'right' ? '#ff3366' : button === 'middle' ? '#ffaa00' : '#00e5ff';
    (document.body || document.documentElement).appendChild(ripple);
    setTimeout(() => ripple.remove(), 400);
    return { x, y, button };
  }

  /** Desenha rastro visual de arrasto entre ponto inicial e final. */
  function showDrag(startX, startY, endX, endY) {
    ensureDOM();
    updatePosition(endX, endY, true);
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'mts-drag-trail');
    svg.style.cssText = 'position:fixed;left:0;top:0;width:100vw;height:100vh;pointer-events:none;z-index:2147483645;';
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', String(startX));
    line.setAttribute('y1', String(startY));
    line.setAttribute('x2', String(endX));
    line.setAttribute('y2', String(endY));
    svg.appendChild(line);
    (document.body || document.documentElement).appendChild(svg);
    setTimeout(() => svg.remove(), 600);
  }

  /** Aplica anel de foco virtual do agente no elemento alvo. */
  function setVirtualFocus(element) {
    if (focusedEl && focusedEl !== element) focusedEl.classList.remove('mts-virtual-focus');
    focusedEl = element;
    if (focusedEl) focusedEl.classList.add('mts-virtual-focus');
  }

  /** Remove o anel de foco virtual ativo. */
  function removeVirtualFocus() {
    if (focusedEl) focusedEl.classList.remove('mts-virtual-focus');
    focusedEl = null;
  }

  window.__BrowserMTS__.virtualCursor = {
    ensureDOM,
    updatePosition,
    showClick,
    showDrag,
    setVirtualFocus,
    removeVirtualFocus,
    getPosition: () => ({ ...currentPos })
  };
})();
