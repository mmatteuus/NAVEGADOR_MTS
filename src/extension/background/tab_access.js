/**
 * @file tab_access.js
 * @description Controle de permissões e concessões de abas com isolamento por sessão.
 */
import { validateTabAccess, getSessionForTab, getTabsForSession,
  claimGrantedTab, restoreGrantedTab, releaseGrantedTab } from './session_registry.js';
import { isGrantedClaim } from './session_registry.js';

const KEY = 'browser_mts_session_tab_grants';
const OWNERS_KEY = 'browser_mts_popup_tab_owners';
let mutationQueue = Promise.resolve();
let ownersLoaded = false;
let ownersLoading = null;

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
async function loadOwners() {
  if (ownersLoaded) return;
  if (!ownersLoading) ownersLoading = (async () => {
    const [data, ids, live] = await Promise.all([
      chrome.storage.session.get(OWNERS_KEY), read(), chrome.tabs.query({})
    ]);
    const allowed = new Set(ids), liveIds = new Set(live.filter(t => isGrantableUrl(t.url)).map(t => t.id));
    const owners = data[OWNERS_KEY] && typeof data[OWNERS_KEY] === 'object' ? data[OWNERS_KEY] : {};
    Object.entries(owners).forEach(([id, sid]) => {
      const tid = Number(id);
      if (sid && allowed.has(tid) && liveIds.has(tid)) restoreGrantedTab(String(sid), tid);
    });
    ownersLoaded = true;
  })();
  await ownersLoading;
}
async function saveOwners() {
  const owners = {};
  for (const id of await read()) { const sid = getSessionForTab(id); if (sid && isGrantedClaim(id)) owners[id] = sid; }
  await chrome.storage.session.set({ [OWNERS_KEY]: owners });
}

async function pruneGrants() {
  await loadOwners();
  const ids = await read(), live = await chrome.tabs.query({});
  const valid = ids.filter(id => live.some(t => t.id === id && isGrantableUrl(t.url)));
  if (valid.length !== ids.length) {
    ids.filter(id => !valid.includes(id)).forEach(releaseGrantedTab);
    await write(valid); await saveOwners();
  }
  return valid;
}
export async function grantedTabs() { return mutate(pruneGrants); }

export async function grantFromPopup(msg, sender) {
  if (!sender || sender.url !== popupUrl()) throw new Error('GRANT_FORBIDDEN');
  const tabs = Array.isArray(msg.tabIds) ? msg.tabIds : [];
  return mutate(async () => { await loadOwners();
    const live = await chrome.tabs.query({}), liveIds = new Set(live.map(t => t.id));
    if (tabs.some(id => !Number.isInteger(id) || id <= 0 || !liveIds.has(id))) throw new Error('TAB_NOT_FOUND');
    if (live.some(t => tabs.includes(t.id) && !isGrantableUrl(t.url))) throw new Error('TAB_NOT_ALLOWED');
    const before = await read(), saved = await write(tabs), after = await chrome.tabs.query({});
    const keep = saved.filter(id => after.some(t => t.id === id));
    before.filter(id => !keep.includes(id)).forEach(releaseGrantedTab);
    await write(keep); await saveOwners(); return read();
  });
}
export async function targetId(requested, sessionId = null) {
  return mutate(async () => {
    const ids = await pruneGrants();
    if (requested !== undefined && requested !== null) {
    const id = Number(requested);
    if (ids.includes(id) && !getSessionForTab(id) && sessionId) { claimGrantedTab(sessionId, id); await saveOwners(); }
    validateTabAccess(sessionId, id);
    if (!ids.includes(id) && !getSessionForTab(id)) throw new Error('TAB_NOT_ALLOWED');
    return id;
    }
    if (sessionId) {
    const sTabs = getTabsForSession(sessionId);
    if (sTabs.length === 1) return sTabs[0];
    if (sTabs.length > 1) throw new Error('TAB_SELECTION_REQUIRED');
    const free = ids.filter(id => !getSessionForTab(id));
    if (free.length === 1) { claimGrantedTab(sessionId, free[0]); await saveOwners(); return free[0]; }
    if (free.length > 1) throw new Error('TAB_SELECTION_REQUIRED');
    throw new Error('TAB_NOT_ALLOWED');
    }
    if (ids.length !== 1) throw new Error('TAB_SELECTION_REQUIRED');
    validateTabAccess(sessionId, ids[0]);
    return ids[0];
  });
}
export async function requireGranted(requested, sessionId = null) {
  const id = await targetId(requested, sessionId), tab = await chrome.tabs.get(id).catch(() => null);
  if (!tab || tab.id !== id || !isGrantableUrl(tab.url)) { await revoke(id); throw new Error('TAB_NOT_ALLOWED'); }
  return tab;
}

export async function revoke(id) {
  return mutate(async () => { await loadOwners(); releaseGrantedTab(id); const next = (await read()).filter(item => item !== Number(id));
    await write(next); await saveOwners(); return next;
  });
}
export async function clearGrants() { return mutate(async () => { await loadOwners(); const ids = await read(); ids.forEach(releaseGrantedTab); await write([]); await saveOwners(); return []; }); }
const toState = (tabs, ids, sid = null) => tabs
  .filter(t => !sid || (ids.includes(t.id) && !getSessionForTab(t.id)) || getSessionForTab(t.id) === sid)
  .map(t => ({
    id: t.id, windowId: t.windowId, title: t.title || '', url: t.url || '',
    active: !!t.active, allowedForAgent: sid ? (ids.includes(t.id) || getSessionForTab(t.id) === sid) : (ids.includes(t.id) || !!getSessionForTab(t.id)),
    selectable: isGrantableUrl(t.url)
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
export async function popupGrantState(currOnly = false, sid = null) {
  return toState(await chrome.tabs.query(currOnly ? { currentWindow: true } : {}), await grantedTabs(), sid);
}
if (typeof chrome !== 'undefined') {
  chrome.tabs?.onRemoved?.addListener((id) => revoke(id).catch(() => {}));
  chrome.tabs?.onReplaced?.addListener((a, r) => revoke(r).then(() => revoke(a)).catch(() => {}));
}
