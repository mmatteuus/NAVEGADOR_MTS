# Performance Journal

## Cookie Isolator Domain Normalization
- **Bottleneck**: `normDom` em `src/extension/background/cookie_isolator.js` invocava incondicionalmente o construtor `URL` dentro de um bloco `try/catch` para cada URL/domínio processado, além de utilizar expressão regular (`.replace(/^\./, '')`) e alocação de array (`.split('/')[0]`).
- **Optimization**: Pular o bloco `try/catch` para domínios sem o protocolo (`://`) e substituir regex/split por operações diretas de string (`charCodeAt`, `indexOf`, `slice`).
- **Impact**: Redução de ~4.32x no tempo total de normalização de domínios em cenários com grande volume de cookies.

## Tunnel Health Status Parsing
- **Bottleneck**: `_status_is_healthy` em `src/core/tunnel_health.py` utilizava expressões geradoras (`next()`, `all()`, `any()`), criando frames de gerador e iterando dicionários via múltiplos chamadas `.get()` redundantes.
- **Optimization**: Substituição das expressões geradoras por loops `for` explícitos com saída antecipada (`break`/`return True`) e verificações booleanas diretas sem alocação de tuplas ou geradores.
- **Impact**: Redução no tempo de verificação de ~0.876s para ~0.265s para 200 mil iterações (ganho de ~3.3x / ~70% mais rápido).
