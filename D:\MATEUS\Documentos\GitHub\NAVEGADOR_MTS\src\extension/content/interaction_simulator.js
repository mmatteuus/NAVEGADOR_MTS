/** Interações web com alvo virtual do agente, sem foco ou seleção globais. */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  const state = { target: null, offset: 0, selection: null };
  const finder = () => window.__BrowserMTS__.elementFinder;
  const editable = (el) => {
    if (!el || el.disabled || el.readOnly) return false;
    if (el.isContentEditable) return true;
    if (el.tagName === 'TEXTAREA') return true;
    if (el.tagName !== 'INPUT') return false;
    return ['text', 'search', 'email', 'url', 'tel', 'password', 'number'].includes(String(el.type || 'text').toLowerCase());
  };
  const textOf = (el) => el.isContentEditable ? (el.textContent || '') : String(el.value ?? '');
  function assertTarget(el) {
    if (!editable(el)) throw new Error('Nenhum campo editável focado foi encontrado para digitação.');
    if (el.isContentEditable && (el.childElementCount || 0) > 0) throw new Error('UNSUPPORTED_TARGET: contenteditable rico não aceita edição virtual segura.');
    if (el.isConnected === false) { state.target = null; throw new Error('TARGET_DISCONNECTED: alvo virtual não está mais no documento.'); }
    if (typeof document.hasFocus === 'function' && document.hasFocus() && document.activeElement === el) throw new Error('TARGET_IN_USE: o campo está sendo usado pelo usuário.');
  }
  function setValue(el, value) {
    if (el.isContentEditable) el.textContent = value;
    else { const desc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value'); if (desc?.set) desc.set.call(el, value); else el.value = value; }
  }
  function emit(el, type, init = {}) {
    const Ctor = type === 'input' || type === 'beforeinput' ? InputEvent : type.startsWith('key') ? KeyboardEvent : Event;
    const event = new Ctor(type, { bubbles: true, cancelable: true, ...init });
    return el.dispatchEvent(event) !== false && !event.defaultPrevented;
  }
  async function resolve(params = {}) {
    const coords = typeof params.x === 'number' && typeof params.y === 'number';
    if (params.selector || params.ref || coords) return finder().findTargetElement(params);
    if (state.target) return state.target;
    throw new Error('Nenhum campo editável focado ou alvo virtual selecionado para o teclado do agente.');
  }
  function choose(el, offset) {
    assertTarget(el);
    if (state.target !== el) { state.target = el; state.offset = offset ?? textOf(el).length; state.selection = null; }
    else if (offset !== undefined) state.offset = offset;
    state.offset = Math.max(0, Math.min(state.offset, textOf(el).length));
    if (state.selection) state.selection = {
      start: Math.min(state.selection.start, textOf(el).length),
      end: Math.min(state.selection.end, textOf(el).length)
    };
    return el;
  }
  function recheck(el) { assertTarget(el); if (state.target !== el) throw new Error('TARGET_INVALID: alvo virtual alterado durante o evento.'); }

  async function clickElement(params) {
    const el = await finder().findTargetElement(params);
    el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'center' });

    const bounds = finder().getElementBounds(el);
    const clickX = params.x ?? bounds.centerX;
    const clickY = params.y ?? bounds.centerY;

    const button = { left: 0, middle: 1, right: 2 }[params.button] ?? 0;
    const eventInit = { bubbles: true, cancelable: true, view: window,
      clientX: clickX, clientY: clickY, button,
      buttons: button === 0 ? 1 : button === 1 ? 4 : 2 };
    el.dispatchEvent(new PointerEvent('pointerdown', eventInit));
    el.dispatchEvent(new MouseEvent('mousedown', eventInit));
    el.dispatchEvent(new PointerEvent('pointerup', eventInit));
    el.dispatchEvent(new MouseEvent('mouseup', eventInit));
    if (button === 0) {
      el.dispatchEvent(new MouseEvent('click', eventInit));
    } else {
      el.dispatchEvent(new MouseEvent('auxclick', eventInit));
      if (button === 2) el.dispatchEvent(new MouseEvent('contextmenu', eventInit));
    }
    if (editable(el)) choose(el);

    return {
      success: true,
      clickedTag: el.tagName.toLowerCase(),
      button: params.button || 'left',
      coordinates: { x: clickX, y: clickY }
    };
  }

  async function typeText(params) {
    const el = choose(await resolve(params));
    if (params.clearFirst) {
      if (emit(el, 'beforeinput', { data: null, inputType: 'deleteContent' })) {
        recheck(el); setValue(el, ''); state.offset = 0; state.selection = null; emit(el, 'input', { data: null, inputType: 'deleteContent' });
      }
    }
    const text = String(params.text || '');
    let typedCharacters = 0;
    for (const char of text) {
      const key = { key: char, code: char.length === 1 ? `Key${char.toUpperCase()}` : '' };
      let started = false;
      try {
        started = true;
        if (!emit(el, 'keydown', key)) continue;
        recheck(el);
        if (!emit(el, 'beforeinput', { data: char, inputType: 'insertText' })) continue;
        recheck(el);
        const value = textOf(el), start = state.selection?.start ?? state.offset, end = state.selection?.end ?? state.offset;
        setValue(el, `${value.slice(0, start)}${char}${value.slice(end)}`); state.offset = start + char.length; state.selection = null; typedCharacters++;
        emit(el, 'input', { data: char, inputType: 'insertText' });
      } finally { if (started) emit(el, 'keyup', key); }
    }
    emit(el, 'change');
    if (params.submit) {
      const key = { key: 'Enter', code: 'Enter', bubbles: true, cancelable: true }; let started = false;
      try {
        started = true;
        if (emit(el, 'keydown', key) && emit(el, 'beforeinput', { data: '\n', inputType: 'insertLineBreak' })) {
          recheck(el);
          if (el.tagName === 'TEXTAREA' || el.isContentEditable) { const value = textOf(el); setValue(el, `${value.slice(0, state.offset)}\n${value.slice(state.offset)}`); state.offset++; emit(el, 'input', { data: '\n', inputType: 'insertLineBreak' }); }
          else if (el.form?.requestSubmit) el.form.requestSubmit(); else if (el.form?.submit) el.form.submit();
        }
      } finally { if (started) emit(el, 'keyup', key); }
    }
    return { success: true, typedCharacters };
  }

  window.__BrowserMTS__.keyboardInternals = { state, textOf, choose, resolve, emit, recheck, setValue };
  window.__BrowserMTS__.interaction = {
    clickElement,
    typeText,
    pressKey: window.__BrowserMTS__.virtualPressKey,
    hoverElement: window.__BrowserMTS__.interactionExtras?.hoverElement,
    selectOption: window.__BrowserMTS__.interactionExtras?.selectOption
  };
})();
