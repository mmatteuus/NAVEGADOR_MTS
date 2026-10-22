/** Garante que o handshake usa a versão efetiva do manifesto da extensão. */
import assert from 'node:assert/strict';

globalThis.chrome = { runtime: { getManifest: () => ({ version: '2.2.0' }) } };
const { buildClientHello } = await import('../src/extension/common/protocol.js');
const hello = buildClientHello({ id: 7 });
assert.equal(hello.type, 'client_hello');
assert.equal(hello.payload.version, '2.2.0');
assert.equal(hello.payload.activeTab.id, 7);
console.log('[PASS] client_hello anuncia a versão atual do manifesto.');
