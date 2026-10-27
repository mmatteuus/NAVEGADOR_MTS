/**
 * @file eval_runner.js
 * @description Executor isolado de scripts customizados (evaluate_js) na página web.
 *
 * Executa expressões e funções JavaScript síncronas ou assíncronas solicitadas
 * pelo agente de IA, capturando exceções e serializando o valor de retorno.
 */

window.__BrowserMTS__ = window.__BrowserMTS__ || {};

(function () {
  /**
   * Executa script JavaScript no contexto seguro da página e aguarda Promises.
   * @param {string} script - Código JavaScript a ser executado.
   * @returns {Promise<object>} Resultado serializado ou detalhes do erro.
   */
  async function evaluateScript(script) {
    if (typeof script !== 'string' || !script.trim()) {
      throw new Error('Nenhum código JavaScript fornecido para avaliação.');
    }

    try {
      // Cria uma função anônima que suporta retorno de valores e await
      const evaluatorFn = new Function(`return (async () => { ${script} })();`);
      const executionResult = await evaluatorFn();

      // Sanitiza o resultado para garantir que pode ser transmitido via JSON
      let serializableResult = executionResult;
      if (typeof executionResult === 'function') {
        serializableResult = executionResult.toString();
      } else if (executionResult instanceof Element) {
        serializableResult = {
          tagName: executionResult.tagName.toLowerCase(),
          id: executionResult.id || null,
          className: executionResult.className || null,
          text: executionResult.textContent?.trim().slice(0, 100)
        };
      }

      return {
        success: true,
        result: serializableResult,
        type: typeof executionResult
      };
    } catch (err) {
      return {
        success: false,
        error: err.message || String(err),
        stack: err.stack || null
      };
    }
  }

  window.__BrowserMTS__.evalRunner = {
    evaluateScript
  };
})();
