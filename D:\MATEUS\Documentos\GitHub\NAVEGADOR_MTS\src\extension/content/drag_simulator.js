/**
 * @file drag_simulator.js
 * @description Simulador de operações de arrasto sintético (drag and drop) no DOM.
 * Emite sequências completas de eventos de arrasto (dragstart, dragover, drop, dragend).
 */
window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  /** Cria envelope mínimo de DataTransfer para simulação de drag DOM. */
  function createDataTransfer() {
    const store = new Map();
    return {
      dropEffect: 'move', effectAllowed: 'all',
      types: ['text/plain'], files: [], items: [],
      setData: (t, val) => store.set(t, String(val)),
      getData: (t) => store.get(t) || '',
      clearData: () => store.clear()
    };
  }

  /**
   * Executa operação sintética de drag & drop entre coordenadas ou elementos.
   * @param {object} params - { startX, startY, endX, endY, selector, targetSelector, steps }
   */
  async function simulateDrag(params = {}) {
    const finder = window.__BrowserMTS__.elementFinder;
    const vCursor = window.__BrowserMTS__.virtualCursor;
    let sourceEl = null, targetEl = null;

    if (params.selector || params.ref) {
      sourceEl = await finder.findTargetElement(params);
    }
    const sBounds = sourceEl ? finder.getElementBounds(sourceEl) : null;
    const startX = params.startX ?? (sBounds ? sBounds.centerX : params.x ?? 0);
    const startY = params.startY ?? (sBounds ? sBounds.centerY : params.y ?? 0);

    if (params.targetSelector) {
      targetEl = await finder.findTargetElement({ selector: params.targetSelector });
    }
    const tBounds = targetEl ? finder.getElementBounds(targetEl) : null;
    const endX = params.endX ?? (tBounds ? tBounds.centerX : startX + 50);
    const endY = params.endY ?? (tBounds ? tBounds.centerY : startY + 50);

    sourceEl = sourceEl || document.elementFromPoint(startX, startY) || document.body;
    targetEl = targetEl || document.elementFromPoint(endX, endY) || sourceEl;

    const dataTransfer = createDataTransfer();
    const btnInit = { bubbles: true, cancelable: true, view: window, clientX: startX, clientY: startY, button: 0, buttons: 1 };

    sourceEl.dispatchEvent(new PointerEvent('pointerdown', btnInit));
    sourceEl.dispatchEvent(new MouseEvent('mousedown', btnInit));

    const dragStartEvt = new DragEvent('dragstart', { ...btnInit, dataTransfer });
    sourceEl.dispatchEvent(dragStartEvt);

    const steps = Math.max(1, params.steps || 4);
    for (let i = 1; i <= steps; i++) {
      const curX = Math.round(startX + ((endX - startX) * i) / steps);
      const curY = Math.round(startY + ((endY - startY) * i) / steps);
      const moveInit = { ...btnInit, clientX: curX, clientY: curY };
      const currentTarget = document.elementFromPoint(curX, curY) || targetEl;
      currentTarget.dispatchEvent(new PointerEvent('pointermove', moveInit));
      currentTarget.dispatchEvent(new MouseEvent('mousemove', moveInit));
      currentTarget.dispatchEvent(new DragEvent('dragover', { ...moveInit, dataTransfer }));
    }

    const dropInit = { ...btnInit, clientX: endX, clientY: endY, dataTransfer };
    targetEl.dispatchEvent(new DragEvent('drop', dropInit));
    sourceEl.dispatchEvent(new DragEvent('dragend', dropInit));
    targetEl.dispatchEvent(new MouseEvent('mouseup', dropInit));
    targetEl.dispatchEvent(new PointerEvent('pointerup', dropInit));

    if (vCursor) {
      vCursor.showDrag(startX, startY, endX, endY);
    }

    return {
      success: true,
      from: { x: startX, y: startY, tag: sourceEl.tagName?.toLowerCase() },
      to: { x: endX, y: endY, tag: targetEl.tagName?.toLowerCase() }
    };
  }

  window.__BrowserMTS__.dragSimulator = { simulateDrag };
})();
