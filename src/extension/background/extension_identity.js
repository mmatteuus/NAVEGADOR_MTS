/** Identidade e metadados persistentes da instalação para o handshake. */
import { buildClientHello } from '../common/protocol.js';
const INSTANCE_KEY = 'browser_mts_extension_instance_id';
const GRANTS_KEY = 'browser_mts_session_tab_grants';
let instancePromise = null;

export async function getClientInstanceId() {
  if (instancePromise) return instancePromise;
  instancePromise = resolveClientInstanceId();
  return instancePromise;
}

async function resolveClientInstanceId() {
  try {
    const saved = await chrome.storage.local.get(INSTANCE_KEY);
    if (typeof saved?.[INSTANCE_KEY] === 'string' && saved[INSTANCE_KEY]) return saved[INSTANCE_KEY];
    const value = globalThis.crypto?.randomUUID?.()
      || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    await chrome.storage.local.set({ [INSTANCE_KEY]: value });
    return value;
  } catch (_) { return ''; }
}

export async function createClientHello(activeTabInfo = null) {
  const hello = buildClientHello(activeTabInfo);
  hello.payload.instanceId = await getClientInstanceId();
  try {
    const saved = await chrome.storage.session.get(GRANTS_KEY);
    hello.payload.grantedTabIds = Array.isArray(saved?.[GRANTS_KEY]) ? saved[GRANTS_KEY] : [];
  } catch (_) { hello.payload.grantedTabIds = []; }
  return hello;
}

export function installGrantSync(sendHello) {
  chrome.storage?.onChanged?.addListener((changes, area) => {
    if (area !== 'session' || !(GRANTS_KEY in changes)) return;
    Promise.resolve().then(sendHello).catch((err) => {
      console.error('Erro na sincronização de concessões:', err);
    });
  });
}
