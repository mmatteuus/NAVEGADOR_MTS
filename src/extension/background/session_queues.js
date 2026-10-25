/**
 * @file session_queues.js
 * @description Filas assíncronas concorrentes segregadas por sessão de agente.
 * Permite que múltiplos agentes executem comandos simultaneamente sem bloqueio mútuo.
 */

const queues = new Map();
let pendingCount = 0;
let idleCallback = null;

/**
 * Enfileira a execução de um comando assíncrono para uma sessão específica.
 * @param {string|null} sessionId - Identificador único da sessão do agente.
 * @param {() => Promise<any>} asyncFn - Função assíncrona a ser executada.
 * @returns {Promise<any>}
 */
export function enqueueSessionCommand(sessionId, asyncFn) {
  const key = sessionId || '__default__';
  const current = queues.get(key) || Promise.resolve();
  pendingCount += 1;
  const next = current.then(asyncFn, asyncFn);
  const tracked = next.finally(() => {
    pendingCount = Math.max(0, pendingCount - 1);
    if (pendingCount === 0 && typeof idleCallback === 'function') idleCallback();
  });
  queues.set(key, tracked.catch(() => {}));
  return next;
}

export function setQueueIdleCallback(callback) { idleCallback = typeof callback === 'function' ? callback : null; }

/**
 * Remove a fila de uma sessão encerrada.
 * @param {string} sessionId
 */
export function removeSessionQueue(sessionId) {
  if (sessionId) queues.delete(sessionId);
}

/**
 * Limpa todas as filas registradas.
 */
export function clearAllSessionQueues() {
  queues.clear(); pendingCount = 0;
  if (typeof idleCallback === 'function') idleCallback();
}

/**
 * Retorna o número de filas ativas.
 * @returns {number}
 */
export function getActiveQueueCount() {
  return pendingCount;
}
