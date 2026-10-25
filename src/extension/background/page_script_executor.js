/** Executa JavaScript no contexto MAIN da aba, fora do CSP da extensão. */
import { getActiveTab } from './tab_manager.js';

async function runInPage(source) {
  function serializeFn(value) {
    if (typeof value === 'function') return value.toString();
    if (typeof Element !== 'undefined' && value instanceof Element) {
      return {
        tagName: value.tagName.toLowerCase(), id: value.id || null,
        className: value.className || null, text: value.textContent?.trim().slice(0, 100) || ''
      };
    }
    if (typeof value === 'bigint') return `${value}n`;
    return value;
  }

  const doc = typeof document !== 'undefined' ? document : null;
  const win = typeof window !== 'undefined' ? window : globalThis;

  if (!doc || typeof doc.createElement !== 'function') {
    return { success: false, error: 'Documento da página indisponível para avaliação de script.' };
  }

  return new Promise((resolve) => {
    const eventName = '__mcp_eval_' + Math.random().toString(36).slice(2);
    const script = doc.createElement('script');
    const handler = (evt) => {
      if (win.removeEventListener) win.removeEventListener(eventName, handler);
      script.remove();
      resolve(evt.detail);
    };
    if (win.addEventListener) win.addEventListener(eventName, handler, { once: true });

    const evtNameStr = JSON.stringify(eventName);
    const serializeStr = serializeFn.toString();

    script.textContent = `(async () => {
      const serialize = ${serializeStr};
      try {
        const raw = await (async () => { ${source} })();
        const detail = { success: true, result: serialize(raw), type: typeof raw };
        window.dispatchEvent(new CustomEvent(${evtNameStr}, { detail }));
      } catch (err) {
        const detail = { success: false, error: err?.message || String(err), stack: err?.stack || null };
        window.dispatchEvent(new CustomEvent(${evtNameStr}, { detail }));
      }
    })();`;

    const target = doc.head || doc.documentElement || doc.body;
    if (target) {
      target.appendChild(script);
      return;
    }
    if (win.removeEventListener) win.removeEventListener(eventName, handler);
    script.remove();
    resolve({ success: false, error: 'Documento da página indisponível para avaliação de script.' });
  });
}

export async function evaluatePageScript(tabId, source) {
  if (typeof source !== 'string' || !source.trim()) {
    throw new Error('Nenhum código JavaScript fornecido para avaliação.');
  }
  const active = tabId ? { id: tabId } : await getActiveTab();
  if (!active?.id) throw new Error('Nenhuma aba ativa localizada para avaliação.');

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: active.id }, world: 'MAIN', func: runInPage, args: [source]
    });
    const result = results?.[0]?.result;
    if (!result) throw new Error('A página não retornou resultado serializável.');
    if (result.success === false) throw new Error(`JavaScript da página falhou: ${result.error}`);
    return result;
  } catch (error) {
    throw new Error(`Falha ao executar JavaScript na página: ${error.message}`);
  }
}
