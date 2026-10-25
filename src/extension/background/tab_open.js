/** Abertura de abas somente pela UI do popup. */
export async function openGrantedTab(message, sender, deps) {
  if (!sender || sender.url !== deps.popupUrl()) throw new Error('GRANT_FORBIDDEN');
  const url = String(message.url || '').trim(); let parsed;
  try { parsed = new URL(url); } catch (_) { throw new Error('URL_NOT_ALLOWED'); }
  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) throw new Error('URL_NOT_ALLOWED');
  return deps.mutate(async () => {
    const tab = await chrome.tabs.create({ url, active: false });
    if (!tab?.id || !Number.isInteger(tab.id)) throw new Error('TAB_CREATE_FAILED');
    return deps.toState(await chrome.tabs.query({}), await deps.write([...(await deps.read()), tab.id]));
  });
}
