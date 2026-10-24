/**
 * @file cookie_isolator.js
 * @description Isolamento e manipulação de cookies/storage por sessão via APIs reais do chrome.cookies e storeId.
 * Nota de Arquitetura: No Chromium, o isolamento estrito de cookies/storage de páginas reais entre múltiplos agentes
 * é assegurado pelo uso de perfis independentes de navegador (User Data Dir / BrowserContext dedicado).
 */
import { logger } from '../common/logger.js';
import { getTabsForSession } from './session_registry.js';

const sessionCookies = new Map(), sessionLocalStorage = new Map(), sessionStores = new Map();
const normDom = u => {
  if (!u) return '';
  if (u.includes('://')) {
    try { return new URL(u).hostname; } catch (_) {}
  }
  let d = u.startsWith('.') ? u.slice(1) : u;
  const slashIdx = d.indexOf('/');
  return slashIdx !== -1 ? d.slice(0, slashIdx) : d;
};

export const bindSessionStore = (sid, stId) => sid && stId && sessionStores.set(String(sid), String(stId));
export const getStoreForSession = sid => sessionStores.get(String(sid)) || null;

export async function resolveCookieStore(sid) {
  if (!sid) return null;
  if (sessionStores.has(sid)) return sessionStores.get(sid);
  try {
    const stores = await globalThis.chrome?.cookies?.getAllCookieStores?.() || [], tabs = getTabsForSession(sid);
    const m = stores.find(s => s.tabIds?.some(t => tabs.includes(t)));
    if (m) { sessionStores.set(sid, m.id); return m.id; }
  } catch (_) {}
  return null;
}

export async function getSessionCookies(sessionId, filter = {}) {
  if (!sessionId) throw new Error('SESSION_REQUIRED: Identificador de sessão obrigatório.');
  const sid = String(sessionId), dom = normDom(filter.domain || filter.url), res = [];
  const storeId = filter.storeId || await resolveCookieStore(sid);
  try {
    const q = { ...filter };
    if (storeId) q.storeId = storeId;
    const realCookies = await globalThis.chrome?.cookies?.getAll?.(q) || [];
    for (const c of realCookies) {
      const cDom = normDom(c.domain);
      if (dom && !cDom.includes(dom) && !dom.includes(cDom)) continue;
      if (filter.name && filter.name !== c.name) continue;
      const mem = sessionCookies.get(sid)?.get(cDom)?.get(c.name);
      if (mem) {
        res.push(storeId && storeId !== '0' ? { ...mem, value: c.value } : mem);
      } else if (storeId && storeId !== '0') {
        res.push(c);
      }
    }
  } catch (err) { logger.warn('Erro ao consultar chrome.cookies:', err.message); }
  const domMap = sessionCookies.get(sid);
  if (domMap) {
    for (const [d, nMap] of domMap) {
      if (!dom || d.includes(dom) || dom.includes(d)) {
        for (const [n, c] of nMap) {
          if ((!filter.name || filter.name === n) && !res.some(r => r.name === n && normDom(r.domain) === d)) {
            res.push(c);
          }
        }
      }
    }
  }
  return filter.asDict ? Object.fromEntries(res.map(c => [c.name, c.value])) : res;
}

export async function setSessionCookie(sessionId, details = {}) {
  if (!sessionId) throw new Error('SESSION_REQUIRED: Identificador de sessão obrigatório.');
  if (!details.name) throw new Error('COOKIE_NAME_REQUIRED: Nome do cookie é obrigatório.');
  const sid = String(sessionId), dom = normDom(details.domain || details.url);
  const storeId = details.storeId || await resolveCookieStore(sid);
  const cookie = { name: details.name, value: details.value ?? '', domain: dom, path: details.path || '/', secure: !!details.secure, httpOnly: !!details.httpOnly, sameSite: details.sameSite || 'lax', storeId: storeId || '0' };
  const pMap = sessionCookies.get(sid) || (sessionCookies.set(sid, new Map()), sessionCookies.get(sid));
  (pMap.get(dom) || (pMap.set(dom, new Map()), pMap.get(dom))).set(details.name, cookie);
  try {
    await globalThis.chrome?.cookies?.set?.({ ...details, url: details.url || `https://${dom}${cookie.path}`, ...(storeId ? { storeId } : {}) });
  } catch (err) { logger.warn('Erro ao gravar no chrome.cookies:', err.message); }
  return { success: true, cookie };
}

export async function clearSessionCookies(sessionId, urlOrFilter = {}) {
  if (!sessionId) throw new Error('SESSION_REQUIRED: Identificador de sessão obrigatório.');
  const sid = String(sessionId), f = typeof urlOrFilter === 'string' ? { url: urlOrFilter } : urlOrFilter;
  const dom = normDom(f.domain || f.url), storeId = f.storeId || await resolveCookieStore(sid), domMap = sessionCookies.get(sid);
  if (domMap) { if (dom) { if (f.name) domMap.get(dom)?.delete(f.name); else domMap.delete(dom); } else domMap.clear(); }
  try { if (f.url && f.name) await globalThis.chrome?.cookies?.remove?.({ url: f.url, name: f.name, ...(storeId ? { storeId } : {}) }); } catch (_) {}
  return { success: true, cleared: true };
}

export function clearSessionStorage(sessionId) {
  if (!sessionId) throw new Error('SESSION_REQUIRED: Identificador de sessão obrigatório.');
  const sid = String(sessionId);
  sessionCookies.delete(sid); sessionLocalStorage.delete(sid); sessionStores.delete(sid);
  return { success: true, sessionId: sid, cleared: true };
}

export function setSessionLocalStorage(sid, origin, key, val) {
  if (!sid || !origin || !key) return false;
  const s = String(sid), m = sessionLocalStorage.get(s) || (sessionLocalStorage.set(s, new Map()), sessionLocalStorage.get(s));
  (m.get(origin) || (m.set(origin, new Map()), m.get(origin))).set(key, val);
  return true;
}

export const getSessionLocalStorage = (sid, origin, key) => (!sid || !origin) ? null : sessionLocalStorage.get(String(sid))?.get(origin)?.get(key) ?? null;
