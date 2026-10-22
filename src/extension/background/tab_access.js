/** Controle de concessões de abas feitas exclusivamente pelo popup confiável. */
const KEY = 'browser_mts_session_tab_grants';
let mutationQueue = Promise.resolve();

export function isGrantableUrl(url) {
  return /^https?:\/\//i.test(String(url || ''));
}

function mutate(task) {
  const result = mutationQueue.then(task, task);
  mutationQueue = result.catch(() => {});
  return result;
}

function popupUrl() {
  return chrome.runtime.getURL('popup/popup.html');
}

async function read() {
  const data = await chrome.storage.session.get(KEY);
  return Array.isArray(data[KEY]) ? data[KEY].map(Number).filter(id => Number.isInteger(id) && id > 0) : [];
}

async function write(ids) {
  await chrome.storage.session.set({ [KEY]: [...new Set(ids.map(Number))] });
  return read();
}

export async function grantedTabs() {
  return mutate(async () => {
    const ids = await read();
    const live = await chrome.tabs.query({});
    const valid = ids.filter(id => live.some(tab => tab.id === id && isGrantableUrl(tab.url)));
    if (valid.length !== ids.length) await write(valid);
    return valid;
  });
}

export async function grantFromPopup(message, sender) {
  if (!sender || sender.url !== popupUrl()) throw new Error('GRANT_FORBIDDEN');
  const tabs = Array.isArray(message.tabIds) ? message.tabIds : [];
  return mutate(async () => {
    const live = await chrome.tabs.query({});
    const liveIds = new Set(live.map(tab => tab.id));
    if (tabs.some(id => !Number.isInteger(id) || id <= 0 || !liveIds.has(id))) throw new Error('TAB_NOT_FOUND');
    if (live.some(tab => tabs.includes(tab.id) && !isGrantableUrl(tab.url))) throw new Error('TAB_NOT_ALLOWED');
    const saved = await write(tabs);
    const after = await chrome.tabs.query({});
    return write(saved.filter(id => after.some(tab => tab.id === id)));
  });
}

export async function targetId(requested) {
  const ids = await grantedTabs();
  if (requested !== undefined && requested !== null) {
    const id = Number(requested);
    if (!ids.includes(id)) throw new Error('TAB_NOT_ALLOWED');
    return id;
  }
  if (ids.length !== 1) throw new Error('TAB_SELECTION_REQUIRED');
  return ids[0];
}

export async function requireGranted(requested) {
  const id = await targetId(requested);
  const tab = await chrome.tabs.get(id).catch(() => null);
  if (!tab || tab.id !== id || !isGrantableUrl(tab.url)) {
    await revoke(id);
    throw new Error('TAB_NOT_ALLOWED');
  }
  return tab;
}

export async function revoke(id) {
  return mutate(async () => write((await read()).filter(item => item !== Number(id))));
}

export async function clearGrants() {
  return mutate(() => write([]));
}

export async function openGrantedTab(message, sender) {
  if (!sender || sender.url !== popupUrl()) throw new Error('GRANT_FORBIDDEN');
  const url = String(message.url || '').trim();
  let parsed;
  try { parsed = new URL(url); } catch (_) { throw new Error('URL_NOT_ALLOWED'); }
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error('URL_NOT_ALLOWED');
  }
  return mutate(async () => {
    const tab = await chrome.tabs.create({ url, active: false });
    if (!tab?.id || !Number.isInteger(tab.id)) throw new Error('TAB_CREATE_FAILED');
    const saved = await write([...(await read()), tab.id]);
    return popupGrantStateFrom(saved);
  });
}

async function popupGrantStateFrom(ids) {
  const tabs = await chrome.tabs.query({});
  return tabs.map(tab => ({
    id: tab.id, windowId: tab.windowId, title: tab.title || '', url: tab.url || '',
    active: !!tab.active, allowedForAgent: ids.includes(tab.id), selectable: isGrantableUrl(tab.url)
  }));
}

export async function popupGrantState(currentWindowOnly = false) {
  const ids = await grantedTabs();
  const tabs = await chrome.tabs.query(currentWindowOnly ? { currentWindow: true } : {});
  return tabs.map(tab => ({
    id: tab.id, windowId: tab.windowId, title: tab.title || '', url: tab.url || '',
    active: !!tab.active, allowedForAgent: ids.includes(tab.id), selectable: isGrantableUrl(tab.url)
  }));
}

chrome.tabs?.onRemoved?.addListener((id) => { revoke(id).catch(() => {}); });
chrome.tabs?.onReplaced?.addListener((added, removed) => {
  revoke(removed).then(() => revoke(added)).catch(() => {});
});
