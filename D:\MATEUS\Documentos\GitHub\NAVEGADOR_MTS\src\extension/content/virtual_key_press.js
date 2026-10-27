/** Edição de teclas no alvo virtual, sem foco ou seleção reais. */
window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  function replaceRange(api, el, data, inputType) {
    if (!api.emit(el, 'beforeinput', { data, inputType })) return false;
    api.recheck(el);
    const value = api.textOf(el);
    const start = api.state.selection?.start ?? api.state.offset;
    const end = api.state.selection?.end ?? api.state.offset;
    api.setValue(el, `${value.slice(0, start)}${data}${value.slice(end)}`);
    api.state.offset = start + data.length;
    api.state.selection = null;
    api.emit(el, 'input', { data, inputType });
    return true;
  }

  function deleteRange(api, el, inputType) {
    if (!api.emit(el, 'beforeinput', { inputType })) return false;
    api.recheck(el);
    const value = api.textOf(el);
    const start = api.state.selection?.start ?? api.state.offset;
    const end = api.state.selection?.end ?? api.state.offset;
    if (start === end) return true;
    api.setValue(el, value.slice(0, start) + value.slice(end));
    api.state.offset = start;
    api.state.selection = null;
    api.emit(el, 'input', { inputType });
    return true;
  }

  window.__BrowserMTS__.virtualPressKey = async function (params = {}) {
    const api = window.__BrowserMTS__.keyboardInternals;
    if (!api) throw new Error('Teclado virtual indisponível nesta página.');
    const modifiers = Array.isArray(params.modifiers) ? params.modifiers : [];
    const el = api.choose(await api.resolve(params));
    const key = params.key || 'Enter';
    const controlSelectAll = modifiers.length === 1 && modifiers[0] === 'Control' && key.toLowerCase() === 'a';
    if (modifiers.length && !controlSelectAll) throw new Error('UNSUPPORTED_SHORTCUT: atalhos dependentes de foco/seleção são bloqueados.');
    const supported = ['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Home', 'End', 'Enter'].includes(key) || key.length === 1;
    if (!supported) throw new Error(`UNSUPPORTED_KEY: ${key} não possui edição virtual segura.`);
    if (controlSelectAll) {
      api.state.selection = { start: 0, end: api.textOf(el).length };
      api.state.offset = api.state.selection.end;
      return { success: true, dispatchedKey: key, selectedAll: true };
    }
    const eventInit = { key, code: key, bubbles: true, cancelable: true };
    let started = false;
    try {
      started = true;
      if (!api.emit(el, 'keydown', eventInit)) return { success: true, dispatchedKey: key, cancelled: true };
      api.recheck(el);
      const value = api.textOf(el);
      const selected = api.state.selection && api.state.selection.end > api.state.selection.start;
      if (selected && (key === 'Backspace' || key === 'Delete')) {
        deleteRange(api, el, 'deleteContentBackward');
      } else if (key === 'Backspace' && api.state.offset > 0) {
        const chars = Array.from(value.slice(0, api.state.offset));
        chars.pop();
        const previousSelection = api.state.selection;
        api.state.selection = { start: chars.join('').length, end: api.state.offset };
        if (!deleteRange(api, el, 'deleteContentBackward')) api.state.selection = previousSelection;
      } else if (key === 'Delete') {
        const chars = Array.from(value.slice(0, api.state.offset));
        const previousSelection = api.state.selection;
        api.state.selection = { start: api.state.offset, end: api.state.offset + (Array.from(value)[chars.length] || '').length };
        if (!deleteRange(api, el, 'deleteContentForward')) api.state.selection = previousSelection;
      } else if (key === 'ArrowLeft') {
        api.state.offset = selected ? api.state.selection.start : Array.from(value.slice(0, api.state.offset)).slice(0, -1).join('').length;
        api.state.selection = null;
      } else if (key === 'ArrowRight') {
        const chars = Array.from(value.slice(0, api.state.offset));
        api.state.offset = selected ? api.state.selection.end : (chars.join('') + (Array.from(value)[chars.length] || '')).length;
        api.state.selection = null;
      } else if (key === 'Home') { api.state.offset = 0; api.state.selection = null;
      } else if (key === 'End') { api.state.offset = value.length; api.state.selection = null;
      } else if (key === 'Enter' && (el.tagName === 'TEXTAREA' || el.isContentEditable)) {
        replaceRange(api, el, '\n', 'insertLineBreak');
      } else if (key === 'Enter') {
        if (el.form?.requestSubmit) el.form.requestSubmit(); else if (el.form?.submit) el.form.submit();
      } else if (key.length === 1) {
        replaceRange(api, el, key, 'insertText');
      }
      return { success: true, dispatchedKey: key, targetElement: el.tagName.toLowerCase() };
    } finally {
      if (started) api.emit(el, 'keyup', eventInit);
    }
  };
})();
