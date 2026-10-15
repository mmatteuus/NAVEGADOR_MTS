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

  try {
    const result = await (0, eval)(`(async () => { ${source} })()`);
    return { success: true, result: serialize(result), type: typeof result };
  } catch (error) {
    return { success: false, error: error.message || String(error), stack: error.stack || null };
  }
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
