import fs from 'node:fs';
import vm from 'node:vm';
import { performance } from 'node:perf_hooks';

const source = fs.readFileSync(new URL('../src/extension/content/dom_extractor.js', import.meta.url), 'utf8');

function createMockDOM(depth, breadth) {
  let idCounter = 0;
  function createNode(d) {
    idCounter++;
    const isText = d === depth || (d > 1 && idCounter % 3 === 0);
    if (isText) {
      return { nodeType: 3, textContent: `  Texto de teste longo para extração do DOM ${idCounter}  ` };
    }
    const children = [];
    if (d < depth) {
      for (let i = 0; i < breadth; i++) {
        children.push(createNode(d + 1));
      }
    }
    return {
      nodeType: 1,
      tagName: ['DIV', 'SPAN', 'P', 'BUTTON', 'A', 'SECTION', 'ARTICLE'][idCounter % 7],
      id: `elem_${idCounter}`,
      className: 'classA classB',
      childNodes: children,
      getAttribute: (attr) => attr === 'role' ? 'button' : attr === 'aria-label' ? `Exemplo de rótulo ${idCounter}` : null
    };
  }
  return createNode(0);
}

const IGNORED_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'PATH', 'TEMPLATE', 'IFRAME']);

// Strategy 1: Array accumulator passed into traverse
function optArray(clean = true, maxDepth = 10, root) {
  let nodeCount = 0;
  const lines = [];

  function traverse(node, depth) {
    if (!node || depth > maxDepth) return;
    if (node.nodeType === 3) {
      const text = node.textContent.trim();
      if (text) lines.push(`${'  '.repeat(depth)}"${text}"\n`);
      return;
    }

    if (node.nodeType !== 1) return;
    if (clean && IGNORED_TAGS.has(node.tagName)) return;

    nodeCount++;
    const tag = node.tagName.toLowerCase();
    let meta = tag;

    if (node.id) meta += `#${node.id}`;
    if (node.className && typeof node.className === 'string') {
      const firstClass = node.className.split(' ')[0];
      if (firstClass) meta += `.${firstClass}`;
    }
    const role = node.getAttribute('role');
    if (role) meta += ` [role="${role}"]`;
    const ariaLabel = node.getAttribute('aria-label');
    if (ariaLabel) meta += ` [label="${ariaLabel}"]`;

    lines.push(`${'  '.repeat(depth)}<${meta}>\n`);
    for (const child of node.childNodes) {
      traverse(child, depth + 1);
    }
  }

  traverse(root, 0);
  return lines.join('');
}

const root = createMockDOM(8, 4);
const context = {
  Node: { TEXT_NODE: 3, ELEMENT_NODE: 1 },
  window: { location: { href: 'https://example.com' } },
  document: {
    body: root,
    documentElement: root,
    title: 'Example',
    location: { href: 'https://example.com' }
  }
};
context.window.window = context.window;
vm.runInNewContext(source, context);
const ext = context.window.__BrowserMTS__.domExtractor;

const origResult = ext.extractCleanDOM().dom;
const optArrayResult = optArray(true, 10, root);
console.log('Match:', origResult === optArrayResult);

const runs = 100;
for (let i = 0; i < 10; i++) {
  ext.extractCleanDOM();
  optArray(true, 10, root);
}

let start = performance.now();
for (let i = 0; i < runs; i++) ext.extractCleanDOM();
const origTime = performance.now() - start;

start = performance.now();
for (let i = 0; i < runs; i++) optArray(true, 10, root);
const arrayTime = performance.now() - start;

console.log('Original time:', origTime.toFixed(2) + 'ms');
console.log('Array accumulator time:', arrayTime.toFixed(2) + 'ms');
