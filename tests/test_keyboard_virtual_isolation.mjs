/** Regressões do teclado web virtual sem foco, seleção ou clipboard globais. */
import assert from 'node:assert/strict';

class MockEvent {
  constructor(type, init = {}) { this.type = type; this.defaultPrevented = false; Object.assign(this, init); }
  preventDefault() { this.defaultPrevented = true; }
}
globalThis.window = globalThis;
globalThis.KeyboardEvent = MockEvent;
globalThis.InputEvent = MockEvent;
globalThis.Event = MockEvent;
globalThis.MouseEvent = MockEvent;
globalThis.PointerEvent = MockEvent;

const events = [];
function input(value) {
  return {
    tagName: 'INPUT', type: 'text', value, disabled: false, readOnly: false,
    scrollIntoView() {},
    dispatchEvent(event) { events.push(event); return !(event.type === 'beforeinput' && this.cancelBeforeInput); }
  };
}
const agentInput = input('old');
let submitted = 0;
agentInput.form = { requestSubmit() { submitted++; } };
const userInput = input('user');
globalThis.document = { activeElement: userInput, hasFocus: () => true };
globalThis.__BrowserMTS__ = { elementFinder: {
  findTargetElement: async ({ selector } = {}) => selector === '#agent' ? agentInput : userInput,
  getElementBounds: () => ({ centerX: 1, centerY: 1 })
} };

await import('../src/extension/content/virtual_key_press.js');
await import('../src/extension/content/interaction_simulator.js');
const interaction = globalThis.__BrowserMTS__.interaction;

await interaction.typeText({ selector: '#agent', text: '🚀' });
assert.equal(agentInput.value, 'old🚀');
assert.equal(document.activeElement, userInput, 'o activeElement do usuário não pode ser alterado');
assert.ok(events.some((event) => event.type === 'beforeinput'));

agentInput.cancelBeforeInput = true;
await interaction.typeText({ selector: '#agent', text: 'X' });
assert.equal(agentInput.value, 'old🚀', 'beforeinput cancelado não pode escrever');

agentInput.isConnected = false;
await assert.rejects(() => interaction.typeText({ text: 'fallback' }), /alvo virtual|TARGET_DISCONNECTED/);
agentInput.isConnected = true;
await assert.rejects(() => interaction.typeText({ selector: '#user', text: 'bloqueado' }), /TARGET_IN_USE/);
agentInput.cancelBeforeInput = false;
const press = await interaction.pressKey({ selector: '#agent', key: 'Backspace' });
assert.equal(press.success, true);
assert.equal(agentInput.value, 'old');
await interaction.pressKey({ selector: '#agent', key: 'a', modifiers: ['Control'] });
await interaction.typeText({ selector: '#agent', text: 'ab' });
await interaction.pressKey({ selector: '#agent', key: 'ArrowLeft' });
await interaction.typeText({ selector: '#agent', text: 'X' });
assert.equal(agentInput.value, 'aXb', 'caret virtual deve ser preservado entre ações');
await interaction.pressKey({ selector: '#agent', key: 'Enter' });
assert.equal(submitted, 1, 'Enter em input deve submeter o formulário');
await interaction.typeText({ selector: '#agent', text: 'abc', clearFirst: true });
await interaction.pressKey({ selector: '#agent', key: 'Home' });
await interaction.pressKey({ selector: '#agent', key: 'Backspace' });
assert.equal(agentInput.value, 'abc', 'Backspace no início não pode inserir o nome da tecla');
agentInput.cancelBeforeInput = true;
await interaction.pressKey({ selector: '#agent', key: 'End' });
await interaction.pressKey({ selector: '#agent', key: 'Backspace' });
agentInput.cancelBeforeInput = false;
await interaction.typeText({ selector: '#agent', text: 'X' });
assert.equal(agentInput.value, 'abcX', 'Backspace cancelado não pode deixar seleção virtual pendente');
console.log('[PASS] teclado virtual preserva foco do usuário e respeita cancelamento.');
