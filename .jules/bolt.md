## 2026-10-25 - Extrator do DOM (`dom_extractor.js`) e Comportamento de Concatenação de Strings no V8

**Aprendizado:**
- Na travessia recursiva de elementos do DOM em JavaScript (V8), a chamada duplicada de APIs do DOM como `node.getAttribute('role')` e `node.getAttribute('aria-label')` realiza buscas redundantes por nó. Armazenar em constantes locais (`role`, `ariaLabel`) evita chamadas repetidas à API nativa do navegador.
- O motor V8 otimiza a concatenação de strings recursiva (`output += ...`) via estruturas de árvore *ConsString* sem cópias imediatas na memória. Contudo, para simplificar e garantir acumulação sem estouro em profundidade, o acúmulo em array de linhas (`lines.push(...)`) seguido por `lines.join('')` unifica a alocação do buffer e gera uma string plana na memória do navegador.

**Ação:**
- Sempre armazenar retornos de `getAttribute` em variáveis temporárias em laços ou travessias no `dom_extractor.js` e em scripts de conteúdo da extensão.
