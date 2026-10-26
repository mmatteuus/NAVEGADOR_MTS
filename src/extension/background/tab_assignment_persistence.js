import { getSessionForTab, isGrantedClaim, restoreGrantedTab, setLastTabForSession } from './session_registry.js';

export function createOwnerPersistence({ key, grantKey, read, isGrantableUrl }) {
  let ownersLoaded = false, ownersLoading = null;
  async function loadOwners() {
    if (ownersLoaded) return;
    if (!ownersLoading) {
      ownersLoading = (async () => {
        const [data, ids, live] = await Promise.all([
          chrome.storage.session.get(key), read(), chrome.tabs.query({})
        ]);
        const allowed = new Set(ids);
        const liveIds = new Set(live.filter(t => isGrantableUrl(t.url) || t.url === 'about:blank').map(t => t.id));
        const owners = data[key] && typeof data[key] === 'object' ? data[key] : {};
        Object.entries(owners).forEach(([id, sid]) => {
          const tid = Number(id);
          if (sid && allowed.has(tid) && liveIds.has(tid)) {
            restoreGrantedTab(String(sid), tid);
            setLastTabForSession(String(sid), tid);
          }
        });
      })().then(() => { ownersLoaded = true; }, error => { ownersLoaded = false; throw error; })
        .finally(() => { ownersLoading = null; });
    }
    return ownersLoading;
  }
  async function saveOwners() {
    const owners = {};
    for (const id of await read()) {
      const sid = getSessionForTab(id);
      if (sid && isGrantedClaim(id)) owners[id] = sid;
    }
    await chrome.storage.session.set({ [key]: owners });
  }
  async function saveState(ids, owners) {
    await chrome.storage.session.set({ [grantKey]: [...new Set(ids.map(Number))], [key]: owners });
  }
  return {
    loadOwners, saveOwners, saveState,
    ownersFor: ids => Object.fromEntries(ids.map(id => [id, getSessionForTab(id)])
      .filter(([id, sid]) => sid && isGrantedClaim(Number(id))))
  };
}
