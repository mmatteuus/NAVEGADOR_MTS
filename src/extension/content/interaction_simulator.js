/**
 * @file interaction_simulator.js
 * @description Simulador de interações humanas em elementos da página web.
 * 
 * Emite sequências completas de eventos nativos (pointer, mouse, teclado e foco)
 * garantindo compatibilidade com frameworks reativos modernos (React, Vue, Angular).
 */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  const finder = window.__BrowserMTS__.elementFinder;

  /**
   * Executa clique simulado com emissão de eventos encadeados.
   * @param {object} params - Parâmetros do comando (selector, ref, x, y, button).
   * @returns {Promise<object>} Confirmação com coordenadas de clique.
   */
  async function clickElement(params) {
    const el = await window.__BrowserMTS__.elementFinder.findTargetElement(params);
    el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'center' });

    const bounds = window.__BrowserMTS__.elementFinder.getElementBounds(el);
    const clickX = params.x ?? bounds.centerX;
    const clickY = params.y ?? bounds.centerY;

    const button = { left: 0, middle: 1, right: 2 }[params.button] ?? 0;
    const eventInit = { bubbles: true, cancelable: true, view: window,
      clientX: clickX, clientY: clickY, button,
      buttons: button === 0 ? 1 : button === 1 ? 4 : 2 };
    el.dispatchEvent(new PointerEvent('pointerdown', eventInit));
    el.dispatchEvent(new MouseEvent('mousedown', eventInit));
    el.focus();
    el.dispatchEvent(new PointerEvent('pointerup', eventInit));
    el.dispatchEvent(new MouseEvent('mouseup', eventInit));
    if (button === 0) {
      el.dispatchEvent(new MouseEvent('click', eventInit));
    } else {
      el.dispatchEvent(new MouseEvent('auxclick', eventInit));
      if (button === 2) el.dispatchEvent(new MouseEvent('contextmenu', eventInit));
    }

    return {
      success: true,
      clickedTag: el.tagName.toLowerCase(),
      button: params.button || 'left',
      coordinates: { x: clickX, y: clickY }
    };
  }

  /**
   * Digita texto em campos de formulário com atualização reativa.
   * @param {object} params - Parâmetros (selector, ref, text, clearFirst, submit).
   * @returns {Promise<object>} Confirmação de caracteres digitados.
   */
  async function typeText(params) {
    const hasTarget = params.selector || params.ref ||
      (typeof params.x === 'number' && typeof params.y === 'number');
    const el = hasTarget ? await window.__BrowserMTS__.elementFinder.findTargetElement(params) : document.activeElement;
    if (!el || !('value' in el || el.isContentEditable)) {
      throw new Error('Nenhum campo editável focado foi encontrado para digitação.');
    }
    if (el.disabled || el.readOnly) throw new Error('O campo focado não aceita digitação.');
    const contentEditable = !!el.isContentEditable;
    el.scrollIntoView({ behavior: 'instant', block: 'center' });
    el.focus();

    if (params.clearFirst) {
      if (contentEditable) el.textContent = '';
      else setNativeValue(el, '');
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }

    const textToType = String(params.text || '');
    let currentVal = contentEditable ? (el.textContent || '') : (el.value ?? '');

    for (const char of textToType) {
      const keyInit = { key: char, bubbles: true, cancelable: true };
      el.dispatchEvent(new KeyboardEvent('keydown', keyInit));
      el.dispatchEvent(new KeyboardEvent('keypress', keyInit));
      currentVal += char;
      if (contentEditable) el.textContent = currentVal;
      else setNativeValue(el, currentVal);
      el.dispatchEvent(new InputEvent('input', { data: char, inputType: 'insertText', bubbles: true }));
      el.dispatchEvent(new KeyboardEvent('keyup', keyInit));
    }

    el.dispatchEvent(new Event('change', { bubbles: true }));

    if (params.submit) {
      el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
      if (el.form) el.form.requestSubmit ? el.form.requestSubmit() : el.form.submit();
    }

    return { success: true, typedCharacters: textToType.length };
  }

  /**
   * Força a atualização do valor de input contornando proxies do React.
   */
  function setNativeValue(element, value) {
    const prototype = Object.getPrototypeOf(element);
    const descriptor = Object.getOwnPropertyDescriptor(prototype, 'value');
    if (descriptor && descriptor.set) {
      descriptor.set.call(element, value);
    } else {
      element.value = value;
    }
  }

  /**
   * Simula foco e efeito de passagem de mouse (hover).
   */
  async function hoverElement(params) {
    const el = await window.__BrowserMTS__.elementFinder.findTargetElement(params);
    el.scrollIntoView({ behavior: 'instant', block: 'center' });
    const bounds = window.__BrowserMTS__.elementFinder.getElementBounds(el);
    const eventInit = { bubbles: true,
      clientX: params.x ?? bounds.centerX, clientY: params.y ?? bounds.centerY };

    el.dispatchEvent(new MouseEvent('mouseover', eventInit));
    el.dispatchEvent(new MouseEvent('mouseenter', eventInit));
    el.dispatchEvent(new MouseEvent('mousemove', eventInit));
    return { success: true, hoveredElement: el.tagName.toLowerCase() };
  }

  /**
   * Seleciona opção em componente <select> nativo.
   */
  async function selectOption(params) {
    const el = await window.__BrowserMTS__.elementFinder.findTargetElement(params);
    if (el.tagName !== 'SELECT') throw new Error('O elemento alvo não é um <select>.');

    const value = Array.isArray(params.values) ? params.values[0] : params.values;
    el.value = value;
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return { success: true, selectedValue: value };
  }

  window.__BrowserMTS__.interaction = {
    clickElement,
    typeText,
    hoverElement,
    selectOption
  };
})();
