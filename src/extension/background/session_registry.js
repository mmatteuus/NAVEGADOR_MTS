/**
 * @file session_registry.js
 * @description Mapeamento estrito e isolamento de abas e janelas por sessão de agente.
 */

const tabToSession = new Map(), sessionToTabs = new Map();
const winToSession = new Map(), sessionToWins = new Map();
const tabSources = new Map(), lastSessionTab = new Map();

export function assignTabToSession(sessionId, tabId) {
  if (!sessionId || tabId == null) return;
  const tid = Number(tabId), sid = String(sessionId);
  releaseTabFromSession(tid);
  tabToSession.set(tid, sid);
  if (!sessionToTabs.has(sid)) sessionToTabs.set(sid, new Set());
  sessionToTabs.get(sid).add(tid);
  tabSources.set(tid, 'agent');
}

export function setLastTabForSession(sessionId, tabId) {
  if (sessionId && tabId != null) lastSessionTab.set(String(sessionId), Number(tabId));
}

export function getLastTabForSession(sessionId) {
  return sessionId ? (lastSessionTab.get(String(sessionId)) || null) : null;
}

export const hasAnySessionTabs = () => tabToSession.size > 0;
export const hasAgentTabs = () => [...tabSources.values()].includes('agent');

export function claimGrantedTab(sessionId, tabId) {
  if (!sessionId || tabId == null) throw new Error('TAB_ACCESS_DENIED: Missing sessionId or tabId.');
  const tid = Number(tabId), owner = getSessionForTab(tid);
  if (owner && owner !== String(sessionId)) {
    throw new Error('TAB_ACCESS_DENIED: The requested tab belongs to another agent session.');
  }
  if (!owner) {
    const sid = String(sessionId);
    tabToSession.set(tid, sid);
    if (!sessionToTabs.has(sid)) sessionToTabs.set(sid, new Set());
    sessionToTabs.get(sid).add(tid);
  }
  tabSources.set(tid, 'popup');
  return true;
}

/** Reassociação explícita feita somente pela UI do popup. */
export function reassignGrantedTab(sessionId, tabId) {
  const tid = Number(tabId), owner = getSessionForTab(tid);
  if (owner && owner !== String(sessionId)) releaseTabFromSession(tid);
  claimGrantedTab(sessionId, tid);
}

export function restoreGrantedTab(sessionId, tabId) {
  if (!getSessionForTab(tabId)) claimGrantedTab(sessionId, tabId);
}

export function releaseGrantedTab(tabId) {
  if (tabSources.get(Number(tabId)) === 'popup') releaseTabFromSession(tabId);
}

export function isGrantedClaim(tabId) {
  const src = tabSources.get(Number(tabId));
  return src === 'popup' || src === 'agent';
}

export function releaseTabFromSession(tabId) {
  const tid = Number(tabId), sid = tabToSession.get(tid);
  if (!sid) return;
  tabToSession.delete(tid); tabSources.delete(tid);
  if (lastSessionTab.get(sid) === tid) lastSessionTab.delete(sid);
  const tabs = sessionToTabs.get(sid);
  if (tabs) { tabs.delete(tid); if (tabs.size === 0) sessionToTabs.delete(sid); }
}

export const getSessionForTab = (tabId) => tabToSession.get(Number(tabId)) || null;
export const getTabsForSession = (sessionId) => sessionId ? Array.from(sessionToTabs.get(String(sessionId)) || []) : [];

export function assignWindowToSession(sessionId, winId) {
  if (!sessionId || winId == null) return;
  const wid = Number(winId), sid = String(sessionId);
  releaseWindowFromSession(wid);
  winToSession.set(wid, sid);
  if (!sessionToWins.has(sid)) sessionToWins.set(sid, new Set());
  sessionToWins.get(sid).add(wid);
}

export function releaseWindowFromSession(winId) {
  const wid = Number(winId), sid = winToSession.get(wid);
  if (!sid) return;
  winToSession.delete(wid);
  const wins = sessionToWins.get(sid);
  if (wins) { wins.delete(wid); if (wins.size === 0) sessionToWins.delete(sid); }
}

export const getSessionForWindow = (winId) => winToSession.get(Number(winId)) || null;
export const getWindowsForSession = (sessionId) => sessionId ? Array.from(sessionToWins.get(String(sessionId)) || []) : [];

export function isTabAllowedForSession(sessionId, tabId) {
  if (tabId == null) return true;
  const tid = Number(tabId), owner = getSessionForTab(tid);
  if (owner) return owner === sessionId;
  return sessionId ? getTabsForSession(sessionId).includes(tid) : true;
}

export function validateTabAccess(sessionId, tabId) {
  if (tabId == null) return true;
  const tid = Number(tabId), owner = getSessionForTab(tid);
  if (owner) {
    if (!sessionId) throw new Error('TAB_ACCESS_DENIED: Sessão do agente não identificada.');
    if (owner !== sessionId) throw new Error('TAB_ACCESS_DENIED: A aba solicitada pertence a outra sessão de agente.');
  } else if (sessionId && !getTabsForSession(sessionId).includes(tid)) {
    throw new Error('TAB_ACCESS_DENIED: A aba solicitada não pertence à sessão do agente.');
  }
  return true;
}

export function clearSessionRegistry() {
  tabToSession.clear(); sessionToTabs.clear(); winToSession.clear(); sessionToWins.clear();
  tabSources.clear(); lastSessionTab.clear();
}

if (typeof chrome !== 'undefined') {
  chrome.tabs?.onRemoved?.addListener(releaseTabFromSession);
  chrome.windows?.onRemoved?.addListener(releaseWindowFromSession);
}
