/** Executa JavaScript no contexto MAIN da aba, fora do CSP da extensão. */
import { getActiveTab } from './tab_manager.js';

async function runInPage(source) {
  function serialize(value) {
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

  return new Promise((resolve) => {
    const eventId = 'mts_eval_' + Math.random().toString(36).slice(2);
    const cleanup = () => {
      window.removeEventListener(eventId, handler);
      clearTimeout(timer);
    };
    const handler = (e) => {
      cleanup();
      resolve(e.detail);
    };
    const timer = setTimeout(() => {
      cleanup();
      resolve({ success: false, error: 'Tempo limite esgotado ou erro de sintaxe no script da página.' });
    }, 5000);
    window.addEventListener(eventId, handler);

    const script = document.createElement('script');
    script.textContent = `(async () => {
      try {
        const __res = await (async () => { ${source} })();
        window.dispatchEvent(new CustomEvent('${eventId}', {
          detail: { success: true, result: (${serialize.toString()})(__res), type: typeof __res }
        }));
      } catch (__err) {
        window.dispatchEvent(new CustomEvent('${eventId}', {
          detail: { success: false, error: __err?.message || String(__err), stack: __err?.stack || null }
        }));
      }
    })();`;
    const target = document.head || document.documentElement || document.body;
    if (target) {
      target.appendChild(script);
      script.remove();
    } else {
      window.removeEventListener(eventId, handler);
      resolve({ success: false, error: 'Elemento raiz DOM indisponível para execução.' });
    }
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
