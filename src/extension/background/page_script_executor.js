/** Executa JavaScript no contexto MAIN da aba, fora do CSP da extensão. */
import { getActiveTab } from './tab_manager.js';

async function runInPage(source) {
  return new Promise((resolve) => {
    const script = document.createElement('script');
    const eventId = Math.random().toString(36).substring(2);
    const eventName = `mcp-eval-${eventId}`;

    const cleanup = () => {
      document.removeEventListener(eventName, listener);
      if (script.parentNode) script.remove();
    };

    const listener = (event) => {
      cleanup();
      const detail = event.detail;
      if (detail && detail.success) {
        resolve({ success: true, result: detail.result, type: detail.type });
      } else {
        resolve({ success: false, error: detail?.error || 'Unknown error', stack: detail?.stack || null });
      }
    };

    document.addEventListener(eventName, listener);

    script.textContent = `
      (async () => {
        function serialize(value) {
          if (typeof value === 'function') return value.toString();
          if (typeof Element !== 'undefined' && value instanceof Element) {
            return {
              tagName: value.tagName.toLowerCase(), id: value.id || null,
              className: value.className || null, text: value.textContent?.trim().slice(0, 100) || ''
            };
          }
          if (typeof value === 'bigint') return \`\${value}n\`;
          return value;
        }
        try {
          const result = await (async () => {
            ${source}
          })();
          document.dispatchEvent(new CustomEvent('${eventName}', {
            detail: { success: true, result: serialize(result), type: typeof result }
          }));
        } catch (error) {
          document.dispatchEvent(new CustomEvent('${eventName}', {
            detail: { success: false, error: error.message || String(error), stack: error.stack || null }
          }));
        }
      })();
    `;

    (document.head || document.documentElement || document).appendChild(script);
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
