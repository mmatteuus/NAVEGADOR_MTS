# Performance Journal - .jules/bolt.md

## 2026-10-25 - Extrator do DOM (dom_extractor.js)
- **Otimização**: Substituição de concatenação direta de strings (`output += traverse(...)`) por acúmulo em `buffer` de array (`buffer.push(...)`) e `buffer.join('')` na função recursiva `extractCleanDOM`.
- **Efeito**: Melhora a alocação de memória e evita re-alocação repetida de strings em árvores DOM de grande escala (~20.000 nós).
- **Verificação**: Testes da extensão executados com sucesso (`node tests/test_dom_extractor.mjs` e `node tests/test_extension_adversarial.mjs`).
