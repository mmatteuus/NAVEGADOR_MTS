/**
 * @file tab_access.js
 * @description Controle de permissões e concessões de abas com isolamento por sessão.
 */
import { validateTabAccess, releaseTabFromSession, getSessionForTab, getTabsForSession } from './session_registry.js';

const KEY = 'browser_mts_session_tab_grants';
let mutationQueue = Promise.resolve();

export const isGrantableUrl = (url) => /^https?:\/\//i.test(String(url || ''));
const popupUrl = () => chrome.runtime.getURL('popup/popup.html');

function mutate(task) {
  const r = mutationQueue.then(task, task);
  mutationQueue = r.catch(() => {});
  return r;
}
const read = async () => {
  const d = await chrome.storage.session.get(KEY);
  return Array.isArray(d[KEY]) ? d[KEY].map(Number).filter(id => Number.isInteger(id) && id > 0) : [];
};
const write = async (ids) => {
  await chrome.storage.session.set({ [KEY]: [...new Set(ids.map(Number))] });
  return read();
};

export async function grantedTabs() {
  return mutate(async () => {
    const ids = await read(), live = await chrome.tabs.query({});
    const valid = ids.filter(id => live.some(t => t.id === id && isGrantableUrl(t.url)));
    return valid.length !== ids.length ? write(valid) : valid;
  });
}

export async function grantFromPopup(msg, sender) {
  if (!sender || sender.url !== popupUrl()) throw new Error('GRANT_FORBIDDEN');
  const tabs = Array.isArray(msg.tabIds) ? msg.tabIds : [];
  return mutate(async () => {
    const live = await chrome.tabs.query({}), liveIds = new Set(live.map(t => t.id));
    if (tabs.some(id => !Number.isInteger(id) || id <= 0 || !liveIds.has(id))) throw new Error('TAB_NOT_FOUND');
    if (live.some(t => tabs.includes(t.id) && !isGrantableUrl(t.url))) throw new Error('TAB_NOT_ALLOWED');
    const saved = await write(tabs), after = await chrome.tabs.query({});
    return write(saved.filter(id => after.some(t => t.id === id)));
  });
}
export async function targetId(requested, sessionId = null) {
  if (requested !== undefined && requested !== null) {
    validateTabAccess(sessionId, requested);
    const id = Number(requested), ids = await grantedTabs();
    if (!ids.includes(id) && !getSessionForTab(id)) throw new Error('TAB_NOT_ALLOWED');
    return id;
  }
  if (sessionId) {
    const sTabs = getTabsForSession(sessionId);
    if (sTabs.length === 1) return sTabs[0];
    if (sTabs.length > 1) throw new Error('TAB_SELECTION_REQUIRED');
  }
  const ids = await grantedTabs();
  if (ids.length !== 1) throw new Error('TAB_SELECTION_REQUIRED');
  validateTabAccess(sessionId, ids[0]);
  return ids[0];
}
export async function requireGranted(requested, sessionId = null) {
  const id = await targetId(requested, sessionId), tab = await chrome.tabs.get(id).catch(() => null);
  if (!tab || tab.id !== id || !isGrantableUrl(tab.url)) { await revoke(id); throw new Error('TAB_NOT_ALLOWED'); }
  return tab;
}

export async function revoke(id) {
  releaseTabFromSession(id);
  return mutate(async () => write((await read()).filter(item => item !== Number(id))));
}
export async function clearGrants() { return mutate(() => write([])); }
const toState = (tabs, ids) => tabs.map(t => ({
  id: t.id, windowId: t.windowId, title: t.title || '', url: t.url || '',
  active: !!t.active, allowedForAgent: ids.includes(t.id) || !!getSessionForTab(t.id), selectable: isGrantableUrl(t.url)
}));

export async function openGrantedTab(message, sender) {
  if (!sender || sender.url !== popupUrl()) throw new Error('GRANT_FORBIDDEN');
  const url = String(message.url || '').trim();
  let p;
  try { p = new URL(url); } catch (_) { throw new Error('URL_NOT_ALLOWED'); }
  if (!['http:', 'https:'].includes(p.protocol) || p.username || p.password) throw new Error('URL_NOT_ALLOWED');
  return mutate(async () => {
    const tab = await chrome.tabs.create({ url, active: false });
    if (!tab?.id || !Number.isInteger(tab.id)) throw new Error('TAB_CREATE_FAILED');
    return toState(await chrome.tabs.query({}), await write([...(await read()), tab.id]));
  });
}
export async function popupGrantState(currOnly = false) {
  return toState(await chrome.tabs.query(currOnly ? { currentWindow: true } : {}), await grantedTabs());
}
if (typeof chrome !== 'undefined') {
  chrome.tabs?.onRemoved?.addListener((id) => revoke(id).catch(() => {}));
  chrome.tabs?.onReplaced?.addListener((a, r) => revoke(r).then(() => revoke(a)).catch(() => {}));
}
