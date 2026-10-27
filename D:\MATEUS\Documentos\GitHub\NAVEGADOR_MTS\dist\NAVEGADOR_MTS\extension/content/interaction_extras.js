/** Interações que não alteram foco: hover e seleção de opção. */
window.__BrowserMTS__ = window.__BrowserMTS__ || {};
(function () {
  const finder = () => window.__BrowserMTS__.elementFinder;
  async function hoverElement(params) {
    const el = await finder().findTargetElement(params);
    el.scrollIntoView({ behavior: 'instant', block: 'center' });
    const b = finder().getElementBounds(el), init = { bubbles: true, clientX: params.x ?? b.centerX, clientY: params.y ?? b.centerY };
    el.dispatchEvent(new MouseEvent('mouseover', init)); el.dispatchEvent(new MouseEvent('mouseenter', init)); el.dispatchEvent(new MouseEvent('mousemove', init));
    return { success: true, hoveredElement: el.tagName.toLowerCase() };
  }
  async function selectOption(params) {
    const el = await finder().findTargetElement(params);
    if (el.tagName !== 'SELECT') throw new Error('O elemento alvo não é um <select>.');
    const value = Array.isArray(params.values) ? params.values[0] : params.values;
    el.value = value; el.dispatchEvent(new Event('change', { bubbles: true }));
    return { success: true, selectedValue: value };
  }
  window.__BrowserMTS__.interactionExtras = { hoverElement, selectOption };
})();
