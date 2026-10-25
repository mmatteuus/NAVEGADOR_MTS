# Performance Journal - BROWSER MTS

## DOM Extraction Optimizations (`src/extension/content/dom_extractor.js`)

- **Array Chunk Accumulation vs Recursive String Concatenation**:
  In recursive DOM tree traversals, appending strings at every recursion level (`output += traverse(...)`) causes excessive intermediate string primitive allocations and GC pressure on large DOM trees. Accumulating fragments in a `chunks` array and joining once with `chunks.join('')` eliminates intermediate allocations.
- **Indentation Caching**:
  Calling `'  '.repeat(depth)` for thousands of nodes allocates redundant string instances. Pre-computing indentation strings in an `indents` array indexed by depth avoids thousands of string allocations.
- **Redundant Attribute Lookups**:
  Caching DOM `node.getAttribute('role')` and `node.getAttribute('aria-label')` into local variables avoids redundant DOM method dispatches during AST formatting.
