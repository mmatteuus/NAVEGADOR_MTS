import {
  validateTabAccess, getSessionForTab, getTabsForSession, assignTabToSession,
  claimGrantedTab, releaseGrantedTab, reassignGrantedTab,
  getLastTabForSession, setLastTabForSession, hasAnySessionTabs
} from './session_registry.js';
import { getAgentDirectory } from './agent_directory.js';
import { openGrantedTab as openTab } from './tab_open.js';
import { createOwnerPersistence } from './tab_assignment_persistence.js';
const KEY = 'browser_mts_session_tab_grants', OWNERS_KEY = 'browser_mts_popup_tab_owners';
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
const ownerStore = createOwnerPersistence({ key: OWNERS_KEY, grantKey: KEY, read, isGrantableUrl });
const { loadOwners, saveOwners } = ownerStore;
async function pruneGrants() {
  await loadOwners();
  const ids = await read(), live = await chrome.tabs.query({});
  const valid = ids.filter(id => live.some(t => t.id === id && (isGrantableUrl(t.url) || (getSessionForTab(id) && (!t.url || t.url === 'about:blank')))));
  if (valid.length !== ids.length) {
    ids.filter(id => !valid.includes(id)).forEach(releaseGrantedTab);
    await write(valid); await saveOwners();
  }
  return valid;
}
export async function grantedTabs() { return mutate(pruneGrants); }
export async function grantAgentTab(sessionId, tabId) {
  const id = Number(tabId);
  if (!Number.isInteger(id) || id <= 0) return;
  if (sessionId) { assignTabToSession(sessionId, id); setLastTabForSession(sessionId, id); }
  return mutate(async () => {
    await loadOwners(); const ids = await read();
    if (!ids.includes(id)) await write([...ids, id]);
    await saveOwners(); return id;
  });
}
export async function grantFromPopup(msg, sender) {
  if (!sender || sender.url !== popupUrl()) throw new Error('GRANT_FORBIDDEN');
  const tabs = Array.isArray(msg.tabIds) ? msg.tabIds : [];
  return mutate(async () => {
    await loadOwners();
    const live = await chrome.tabs.query({}), liveIds = new Set(live.map(t => t.id));
    if (tabs.some(id => !Number.isInteger(id) || id <= 0 || !liveIds.has(id))) throw new Error('TAB_NOT_FOUND');
    if (live.some(t => tabs.includes(t.id) && !isGrantableUrl(t.url))) throw new Error('TAB_NOT_ALLOWED');
    const before = await read(), saved = await write(tabs), keep = saved.filter(id => liveIds.has(id));
    before.filter(id => !keep.includes(id)).forEach(releaseGrantedTab);
    await write(keep); await saveOwners(); return read();
  });
}
export async function assignFromPopup(msg, sender) {
  if (!sender || sender.url !== popupUrl()) throw new Error('GRANT_FORBIDDEN');
  const assignments = Array.isArray(msg.assignments) ? msg.assignments : [];
  return mutate(async () => {
    await loadOwners();
    const revocations = Array.isArray(msg.revocations) ? msg.revocations : [];
    for (const item of revocations) {
      if (getSessionForTab(Number(item?.tabId)) !== (String(item?.expectedSessionId || '') || null)) throw new Error('AGENT_ASSIGNMENT_STALE');
    }
    const agents = new Set(getAgentDirectory().filter(a => a.connected).map(a => a.sessionId));
    const live = await chrome.tabs.query({}), byId = new Map(live.map(tab => [tab.id, tab]));
    for (const item of assignments) {
      const id = Number(item?.tabId), sid = String(item?.sessionId || '');
      if (!Number.isInteger(id) || !byId.has(id)) throw new Error('TAB_NOT_FOUND');
      if (!isGrantableUrl(byId.get(id).url)) throw new Error('TAB_NOT_ALLOWED');
      if (!agents.has(sid)) throw new Error('AGENT_NOT_AVAILABLE');
      if (getSessionForTab(id) !== (String(item?.expectedSessionId || '') || null)) throw new Error('AGENT_ASSIGNMENT_STALE');
    }
    const before = await read(), ids = new Set(before), owners = ownerStore.ownersFor(before);
    revocations.forEach(item => { const id = Number(item.tabId); ids.delete(id); delete owners[id]; });
    assignments.forEach(item => { const id = Number(item.tabId); ids.add(id); owners[id] = String(item.sessionId); });
    await ownerStore.saveState([...ids], owners);
    revocations.forEach(item => releaseGrantedTab(Number(item.tabId)));
    assignments.forEach(item => reassignGrantedTab(item.sessionId, item.tabId));
    return read();
  });
}
async function autoGrantActiveTab(sessionId) {
  const activeTabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const candidate = activeTabs.find(t => t?.id && isGrantableUrl(t.url));
  if (!candidate) return null;
  await write([candidate.id]);
  if (sessionId) { claimGrantedTab(sessionId, candidate.id); setLastTabForSession(sessionId, candidate.id); await saveOwners(); }
  return candidate.id;
}
export async function targetId(requested, sessionId = null) {
  return mutate(async () => {
    const ids = await pruneGrants();
    if (requested !== undefined && requested !== null) {
      const id = Number(requested);
      if (ids.includes(id) && !getSessionForTab(id) && sessionId) {
        claimGrantedTab(sessionId, id); await saveOwners();
      } else if (ids.length === 0 && !hasAnySessionTabs() && !getSessionForTab(id) && Number.isInteger(id) && id > 0) {
        const live = await chrome.tabs.get(id).catch(() => null);
        if (live && isGrantableUrl(live.url)) {
          await write([id]);
          if (sessionId) { claimGrantedTab(sessionId, id); setLastTabForSession(sessionId, id); await saveOwners(); }
          return id;
        }
      }
      validateTabAccess(sessionId, id);
      if (!ids.includes(id) && !getSessionForTab(id)) throw new Error('TAB_NOT_ALLOWED');
      if (sessionId) setLastTabForSession(sessionId, id);
      return id;
    }
    if (sessionId) {
      let sTabs = getTabsForSession(sessionId);
      if (sTabs.length === 0 && String(sessionId).startsWith('sess_')) sTabs = getTabsForSession('tunnel_default');
      const last = getLastTabForSession(sessionId) || getLastTabForSession('tunnel_default');
      if (sTabs.length === 1) return sTabs[0];
      if (sTabs.length > 1) { if (last && sTabs.includes(last)) return last; throw new Error('TAB_SELECTION_REQUIRED'); }
      const free = ids.filter(id => !getSessionForTab(id));
      if (free.length === 1) { claimGrantedTab(sessionId, free[0]); await saveOwners(); return free[0]; }
      if (free.length > 1) throw new Error('TAB_SELECTION_REQUIRED');
      if (ids.length === 0 && !hasAnySessionTabs()) { const auto = await autoGrantActiveTab(sessionId); if (auto) return auto; }
      throw new Error('TAB_NOT_ALLOWED');
    }
    if (ids.length === 0 && !hasAnySessionTabs()) { const auto = await autoGrantActiveTab(null); if (auto) return auto; }
    if (ids.length !== 1) throw new Error('TAB_SELECTION_REQUIRED');
    validateTabAccess(sessionId, ids[0]); return ids[0];
  });
}
export async function requireGranted(requested, sessionId = null) {
  const id = await targetId(requested, sessionId), tab = await chrome.tabs.get(id).catch(() => null);
  if (!tab || tab.id !== id || !isGrantableUrl(tab.url)) { await revoke(id); throw new Error('TAB_NOT_ALLOWED'); }
  return tab;
}
export async function revoke(id) { return mutate(async () => { await loadOwners(); releaseGrantedTab(id); const next = (await read()).filter(item => item !== Number(id)); await write(next); await saveOwners(); return next; }); }
export async function clearGrants() { return mutate(async () => { await loadOwners(); const ids = await read(); ids.forEach(releaseGrantedTab); await write([]); await saveOwners(); return []; }); }
const toState = (tabs, ids, sid = null) => tabs.filter(t => !sid || (ids.includes(t.id) && !getSessionForTab(t.id)) || getSessionForTab(t.id) === sid).map(t => ({ id: t.id, windowId: t.windowId, title: t.title || '', url: t.url || '', active: !!t.active, allowedForAgent: sid ? (ids.includes(t.id) || getSessionForTab(t.id) === sid) : (ids.includes(t.id) || !!getSessionForTab(t.id)), selectable: isGrantableUrl(t.url), sessionId: getSessionForTab(t.id) }));
export async function openGrantedTab(message, sender) { return openTab(message, sender, { popupUrl, mutate, read, write, toState }); }
export async function popupGrantState(currOnly = false, sid = null) { return toState(await chrome.tabs.query(currOnly ? { currentWindow: true } : {}), await grantedTabs(), sid); }
if (typeof chrome !== 'undefined') { chrome.tabs?.onRemoved?.addListener((id) => revoke(id).catch(() => {})); chrome.tabs?.onReplaced?.addListener((a, r) => revoke(r).then(() => revoke(a)).catch(() => {})); }
