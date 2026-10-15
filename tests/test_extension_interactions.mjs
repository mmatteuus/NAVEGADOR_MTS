/** Regressões de botão e digitação em contenteditable. */
import assert from 'node:assert/strict';

class MockEvent { constructor(type, init = {}) { this.type = type; Object.assign(this, init); } }
globalThis.window = globalThis;
globalThis.PointerEvent = MockEvent;
globalThis.MouseEvent = MockEvent;
globalThis.KeyboardEvent = MockEvent;
globalThis.InputEvent = MockEvent;
globalThis.Event = MockEvent;

const events = [];
const button = {
  tagName: 'BUTTON',
  scrollIntoView() {},
  focus() { document.activeElement = this; },
  dispatchEvent(event) { events.push(event); }
};
const editable = {
  tagName: 'DIV', isContentEditable: true, textContent: 'old',
  scrollIntoView() {}, focus() { document.activeElement = this; },
  dispatchEvent(event) { events.push(event); }
};
globalThis.document = { activeElement: editable };
globalThis.__BrowserMTS__ = { elementFinder: {
  findTargetElement: async () => button,
  getElementBounds: () => ({ centerX: 10, centerY: 20 })
} };

await import('../src/extension/content/interaction_simulator.js');
const interaction = globalThis.__BrowserMTS__.interaction;
events.length = 0;
await interaction.clickElement({ button: 'right' });
assert.deepEqual(events.filter((event) => ['click', 'auxclick', 'contextmenu'].includes(event.type))
  .map((event) => [event.type, event.button]), [['auxclick', 2], ['contextmenu', 2]]);

events.length = 0;
await interaction.clickElement({ button: 'middle' });
assert.deepEqual(events.filter((event) => ['click', 'auxclick', 'contextmenu'].includes(event.type))
  .map((event) => [event.type, event.button]), [['auxclick', 1]]);

events.length = 0;
document.activeElement = editable;
await interaction.typeText({ text: 'X' });
assert.equal(editable.textContent, 'oldX');
await interaction.typeText({ text: 'Y', clearFirst: true });
assert.equal(editable.textContent, 'Y');
console.log('[PASS] botões e contenteditable respeitam o contrato.');
