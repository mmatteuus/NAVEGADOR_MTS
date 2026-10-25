# Bolt Performance Journal

## DOM Traversal & Extraction (`src/extension/content/dom_extractor.js`)

- **Pre-computed Lookup Tables vs Dynamic String Allocation**: Repeatedly calling `'  '.repeat(depth)` during deep tree traversal creates high garbage collection pressure. Pre-computing indentation strings in an `INDENTS` array up to max depth eliminates string allocation per node.
- **DOM Attribute Access Caching**: Calling `node.getAttribute('role')` and `node.getAttribute('aria-label')` multiple times in condition checks vs assignment statements introduces redundant DOM binding calls. Caching in local variables halved execution overhead when combined with indexed iteration.
- **NodeList Iteration**: `for...of` loops on DOM `NodeList` collections instantiate iterator objects for every element node. Using an indexed `for` loop with cached length (`children.length`) avoids iterator allocation per node.
- **Measured Impact**: Extraction time for 20,000 nodes dropped from ~50.30ms to ~26.16ms per run (1.92x speedup / ~48% reduction in execution time).
