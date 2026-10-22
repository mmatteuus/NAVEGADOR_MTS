/**
 * @file keyboard_scroll.js
 * @description Controle de teclas especiais e rolagem de página para automação web.
 * 
 * Permite disparo de teclas como Enter, Tab, Escape e setas com teclas modificadoras,
 * além de rolagem suave tanto na janela global quanto em contêineres internos.
 */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  /**
   * Pressiona uma tecla física com suporte a modificadores no elemento em foco.
   * @param {object} params - Parâmetros (key, modifiers).
   * @returns {object} Confirmação da tecla disparada.
   */
  function pressKey(params) {
    const interaction = window.__BrowserMTS__.interaction;
    if (!interaction?.pressKey) throw new Error('Teclado virtual indisponível nesta página.');
    return interaction.pressKey(params);
  }

  /**
   * Rola a janela ou um container rolável específico.
   * @param {object} params - Parâmetros (direction, amount, selector).
   * @returns {object} Posições x, y resultantes da rolagem.
   */
  function scrollPage(params) {
    const direction = params.direction || 'down';
    const amount = Number(params.amount) || 400;
    const target = params.selector ? document.querySelector(params.selector) : window;

    let deltaX = 0;
    let deltaY = 0;

    switch (direction) {
      case 'up':
        deltaY = -amount;
        break;
      case 'down':
        deltaY = amount;
        break;
      case 'left':
        deltaX = -amount;
        break;
      case 'right':
        deltaX = amount;
        break;
      default:
        deltaY = amount;
    }

    if (target === window) {
      window.scrollBy({ left: deltaX, top: deltaY, behavior: 'smooth' });
      return {
        success: true,
        scrollX: window.scrollX,
        scrollY: window.scrollY
      };
    }

    if (target && target instanceof Element) {
      target.scrollBy({ left: deltaX, top: deltaY, behavior: 'smooth' });
      return {
        success: true,
        scrollLeft: target.scrollLeft,
        scrollTop: target.scrollTop
      };
    }

    throw new Error(`Elemento de rolagem não encontrado: '${params.selector}'`);
  }

  window.__BrowserMTS__.keyboardScroll = {
    pressKey,
    scrollPage
  };
})();
