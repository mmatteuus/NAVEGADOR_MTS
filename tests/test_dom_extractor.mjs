/** Regressões do snapshot: texto visível limitado e campos sensíveis. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../src/extension/content/dom_extractor.js', import.meta.url), 'utf8');
const elements = [
  { tagName: 'INPUT', type: 'password', value: 'segredo', offsetParent: {}, getAttribute: () => null, setAttribute: () => {}, innerText: '', placeholder: '' },
  { tagName: 'A', type: '', value: '', offsetParent: {}, getAttribute: () => null, setAttribute: () => {}, innerText: 'Learn more', placeholder: '' }
];
const body = { innerText: 'Título visível\nUm parágrafo que o agente precisa ler.' };
const context = { Node: { TEXT_NODE: 3, ELEMENT_NODE: 1 }, window: { location: { href: 'https://example.com' } }, document: {
  body, documentElement: body, title: 'Example', location: { href: 'https://example.com' },
  querySelectorAll: () => elements
} };
context.window.window = context.window;
vm.runInNewContext(source, context);

const result = context.window.__BrowserMTS__.domExtractor.extractAriaSnapshot();
assert.match(result.snapshot, /Título visível/);
assert.match(result.snapshot, /Um parágrafo que o agente precisa ler/);
assert.match(result.snapshot, /Learn more/);
assert.doesNotMatch(result.snapshot, /segredo/);
assert.equal(result.visibleTextTruncated, false);

body.innerText = 'x'.repeat(20001);
const truncated = context.window.__BrowserMTS__.domExtractor.extractAriaSnapshot();
assert.equal(truncated.visibleText.length, 20000);
assert.equal(truncated.visibleTextTruncated, true);
assert.match(truncated.snapshot, /texto visível truncado/);
console.log('PASS: snapshot inclui texto visível limitado e não expõe senha.');
