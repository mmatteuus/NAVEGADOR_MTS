/** E2E opt-in: extensão real, popup, ponte WebSocket e roteador MCP em Chromium. */
import assert from 'node:assert/strict';
import { setup } from './keyboard_e2e_runtime.mjs';

const env = await setup();
const { page, popup, context, worker, call, save, tabId, url } = env;
try {
  await call('browser_type', { tabId, selector: '#agent', text: 'bloqueado' }, /TAB_NOT_ALLOWED/);
  await save([tabId]);
  await page.bringToFront();
  await page.locator('#user').focus();
  await page.keyboard.type('MEU');
  await call('browser_type', { selector: '#agent', text: 'ABC' });
  assert.equal(await page.locator('#agent').inputValue(), 'ABC');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'user');
  await call('browser_press_key', { key: 'ArrowLeft' });
  await call('browser_type', { text: '😀' });
  assert.equal(await page.locator('#agent').inputValue(), 'AB😀C');
  await call('browser_press_key', { key: 'Backspace' });
  assert.equal(await page.locator('#agent').inputValue(), 'ABC');
  await Promise.all([page.keyboard.type(' TEXTO'), call('browser_type', { text: '🚀' })]);
  assert.equal(await page.locator('#user').inputValue(), 'MEU TEXTO');
  assert.equal(await page.locator('#agent').inputValue(), 'AB🚀C');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'user');
  await call('browser_type', { selector: '#user', text: 'INTRUSO' }, /TARGET_IN_USE/);
  assert.equal(await page.locator('#user').inputValue(), 'MEU TEXTO');
  await call('browser_type', { selector: '#check', text: 'x' }, /editável|UNSUPPORTED/);
  await call('browser_type', { selector: '#rich', text: 'x' }, /UNSUPPORTED/);
  await call('browser_press_key', { selector: '#agent', key: 'a', modifiers: ['Control'] });
  await call('browser_type', { text: 'NOVO' });
  assert.equal(await page.locator('#agent').inputValue(), 'NOVO');
  await page.evaluate(() => {
    document.querySelector('#agent').addEventListener('beforeinput', event => {
      window.lastBeforeInput = { data: event.data, inputType: event.inputType };
      if (event.data === '!') event.preventDefault();
    });
  });
  const cancelled = await call('browser_type', { text: '!' });
  assert.equal(cancelled.typedCharacters, 0);
  assert.equal(await page.locator('#agent').inputValue(), 'NOVO');
  assert.deepEqual(await page.evaluate(() => window.lastBeforeInput), { data: '!', inputType: 'insertText' });
  await call('browser_type', { text: 'OK', clearFirst: true, submit: true });
  assert.equal(await page.evaluate(() => window.submissions), 1);
  await call('browser_type', { selector: '#area', text: 'linha' });
  await call('browser_press_key', { key: 'Enter' });
  await call('browser_type', { text: 'dois' });
  assert.equal(await page.locator('#area').inputValue(), 'linha\ndois');
  await call('browser_press_key', { key: 'a', modifiers: ['Control'] });
  await call('browser_press_key', { key: 'Backspace' });
  assert.equal(await page.locator('#area').inputValue(), '');
  const beforeTabs = await worker.evaluate(() => chrome.tabs.query({ active: true, currentWindow: true }));
  // Abertura e concessão ocorrem pelo mesmo botão que o usuário utiliza no popup.
  await popup.locator('#new-agent-tab-url').fill(`${url}/?nova`);
  await popup.locator('#open-agent-tab').click();
  await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('liberada'));
  const tabs = await call('browser_manage_tabs', { action: 'list', currentWindowOnly: false });
  const fresh = tabs.find(tab => tab.url.includes('?nova'));
  assert.ok(fresh?.allowedForAgent);
  assert.equal(fresh.active, false);
  const afterTabs = await worker.evaluate(() => chrome.tabs.query({ active: true, currentWindow: true }));
  assert.equal(afterTabs[0].id, beforeTabs[0].id);
  await call('browser_type', { selector: '#agent', text: 'ambíguo' }, /TAB_SELECTION_REQUIRED/);
  await call('browser_type', { tabId: fresh.id, selector: '#agent', text: 'SEGUNDO' });
  const freshPage = context.pages().find(candidate => candidate.url().includes('?nova'));
  assert.equal(await freshPage.locator('#agent').inputValue(), 'SEGUNDO');
  assert.equal(await page.locator('#user').inputValue(), 'MEU TEXTO');
  await save([tabId]);
  await call('browser_snapshot', { tabId: fresh.id }, /TAB_NOT_ALLOWED/);
  await call('browser_navigate', { tabId, url: `${url}/?navegada` });
  await page.waitForURL('**/?navegada');
  await call('browser_type', { tabId, selector: '#agent', text: 'NAVEGOU' });
  assert.equal(await page.locator('#agent').inputValue(), 'NAVEGOU');
  await popup.reload();
  await popup.locator('#tab-access-list input').first().waitFor();
  await popup.screenshot({ path: `${env.folder}/popup-guias.png`, fullPage: true });
  await popup.locator('#clear-tab-grants').click();
  await popup.waitForFunction(() => document.querySelector('#tab-access-message').textContent.includes('limpa'));
  assert.equal(await popup.locator('#tab-access-list input:checked').count(), 0);
  assert.ok(await popup.locator(`#tab-access-list input[value="${tabId}"]`).count());
  await call('browser_snapshot', { tabId }, /TAB_NOT_ALLOWED/);
  await save([tabId]);
  const restarted = await env.restart();
  assert.deepEqual(await restarted.evaluate(async () => {
    const saved = await chrome.storage.session.get('browser_mts_session_tab_grants');
    return saved.browser_mts_session_tab_grants || [];
  }), []);
  console.log('PASS E2E: foco/teclado simultâneo, Unicode/caret, eventos, popup uma/muitas/nova, revogação e navegação');
  console.log(`Artefatos descartáveis: ${env.folder}`);
} finally {
  await env.close();
}
