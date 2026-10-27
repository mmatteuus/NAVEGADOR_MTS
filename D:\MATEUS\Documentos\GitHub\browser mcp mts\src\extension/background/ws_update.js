/** Coordena recarga segura da extensão após atualização do Desktop App. */

export const UPDATE_STATE_KEY = 'browser_mts_extension_update_state';

const DEFAULT_STATE = Object.freeze({
  status: 'idle',
  targetVersion: '',
  actualVersion: '',
  error: '',
  requestedAt: 0
});

let idleCheck = () => true;
let idleWaiters = [];
let updateAdmissionBlocked = false;
let updateOperation = null;

function normalizeVersion(value) {
  const parts = String(value || '').trim().replace(/^v/i, '').split('.');
  if (!parts.length || parts.some(part => !/^\d+$/.test(part))) return null;
  return parts.map(Number);
}

function compareVersions(left, right) {
  const a = normalizeVersion(left) || [0];
  const b = normalizeVersion(right) || [0];
  for (let index = 0; index < Math.max(a.length, b.length); index += 1) {
    if ((a[index] || 0) !== (b[index] || 0)) return (a[index] || 0) > (b[index] || 0) ? 1 : -1;
  }
  return 0;
}

async function readState() {
  try {
    const saved = await chrome.storage.local.get(UPDATE_STATE_KEY);
    return { ...DEFAULT_STATE, ...(saved?.[UPDATE_STATE_KEY] || {}) };
  } catch (_) { return { ...DEFAULT_STATE, storageError: true }; }
}

async function writeState(next) {
  const state = { ...DEFAULT_STATE, ...next };
  try { await chrome.storage.local.set({ [UPDATE_STATE_KEY]: state }); return state; }
  catch (_) { return { ...state, storageError: true }; }
}

export function setUpdateIdleCheck(checker) {
  idleCheck = typeof checker === 'function' ? checker : () => true;
  flushIdleWaiters();
}

export function notifyUpdateQueueIdle() { flushIdleWaiters(); }

function flushIdleWaiters() {
  if (!idleCheck()) return;
  const waiters = idleWaiters;
  idleWaiters = [];
  waiters.forEach(resolve => resolve());
}

export function waitForUpdateQueueIdle() {
  if (idleCheck()) return Promise.resolve();
  return new Promise(resolve => idleWaiters.push(resolve));
}

export async function getExtensionUpdateState() { return readState(); }

export async function confirmExtensionVersion(actualVersion, error = '') {
  const current = await readState();
  if (error) { updateAdmissionBlocked = false; return writeState({ ...current, status: 'error', error: String(error), actualVersion: String(actualVersion || '') }); }
  if (!current.targetVersion || compareVersions(actualVersion, current.targetVersion) >= 0) {
    updateAdmissionBlocked = false;
    return writeState({ ...current, status: 'confirmed', actualVersion: String(actualVersion || ''), error: '' });
  }
  if (current.status === 'reloading') {
    return writeState({ ...current, status: 'error', actualVersion: String(actualVersion || ''), error: 'A extensão recarregou, mas continua com a versão antiga.' });
  }
  return current;
}

/** Processa o pedido do Desktop App; cada versão alvo recebe no máximo uma recarga. */
async function processExtensionUpdate(payload = {}) {
  const target = String(payload.desktopVersion || payload.targetVersion || '').trim();
  // A versão do manifesto local é a única fonte confiável; o payload vem da ponte.
  const actual = String(getManifestVersion()).trim();
  if (!target || !normalizeVersion(target)) return { ...(await readState()), action: 'ignored' };
  if (compareVersions(actual, target) >= 0) {
    return { ...(await confirmExtensionVersion(actual)), action: 'confirmed' };
  }
  const current = await readState();
  if (current.storageError) {
    return { ...current, status: 'error', error: 'Não foi possível persistir o estado da atualização.', action: 'error' };
  }
  if (current.targetVersion === target && (current.requestedAt > 0 || current.status === 'confirmed')) {
    if (current.status === 'reloading') await confirmExtensionVersion(actual);
    return { ...current, action: 'already_requested' };
  }
  if (payload.reloadRequired === false) {
    updateAdmissionBlocked = false;
    return { ...(await writeState({ ...current, targetVersion: target, actualVersion: actual, status: 'error', error: payload.extensionUpdateMessage || 'A extensão está em uma pasta externa.' })), action: 'diagnostic' };
  }
  updateAdmissionBlocked = true;
  const pending = await writeState({ ...current, targetVersion: target, actualVersion: actual, status: 'pending', error: '' });
  if (pending.storageError) {
    updateAdmissionBlocked = false;
    return { ...pending, status: 'error', error: 'Não foi possível persistir o estado da atualização.', action: 'error' };
  }
  await waitForUpdateQueueIdle();
  const reloading = await writeState({ ...pending, status: 'reloading', requestedAt: Date.now() });
  if (reloading.storageError) {
    updateAdmissionBlocked = false;
    return { ...reloading, status: 'error', error: 'Não foi possível persistir o pedido de recarga.', action: 'error' };
  }
  try {
    if (typeof chrome?.runtime?.reload !== 'function') throw new Error('chrome.runtime.reload indisponível.');
    chrome.runtime.reload();
  } catch (error) {
    updateAdmissionBlocked = false;
    return { ...(await writeState({ ...reloading, status: 'error', error: error.message })), action: 'error' };
  }
  return { ...reloading, action: 'reload_requested' };
}

export function handleExtensionUpdate(payload = {}) {
  if (updateOperation) return updateOperation.then(state => ({ ...state, action: 'already_requested' }));
  updateOperation = processExtensionUpdate(payload).finally(() => { updateOperation = null; });
  return updateOperation;
}

export function isUpdateAdmissionBlocked() { return updateAdmissionBlocked; }

function getManifestVersion() {
  try { return chrome.runtime.getManifest?.().version || ''; } catch (_) { return ''; }
}
