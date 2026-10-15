# AGENTS.md

## O que é este repo

App desktop **Windows 11 apenas** (Python + CustomTkinter) que unifica: servidor MCP (stdio + WebSocket), extensão Chrome/Edge Manifest V3 (JS puro) e módulo de Computer Use (mouse/teclado/tela via ctypes). Código, comentários e docs em **Português do Brasil**.

## Comandos (verificados nesta máquina)

```powershell
# Ambiente (já existe em .venv/; recriar se necessário)
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# Suíte completa: 92 testes, ~30s, deve passar 100%
.venv\Scripts\python -m pytest -q

# Um módulo específico
.venv\Scripts\python -m pytest tests/test_safety_gate.py -v

# Testes adversariais da extensão MV3 (requer Node 18+)
node tests/test_extension_adversarial.mjs

# Rodar o app
python entrypoint.py            # UI (flags: --stdio = servidor MCP stdio, --minimized = bandeja)

# Gerar instalador .exe (PyInstaller + Inno Setup 6, usa .venv)
COMPILAR_INSTALADOR.bat      # saída em dist_installer\
```

- CI de testes selecionados e artefato Windows: `.github/workflows/windows-qa.yml`; execução depende de runners habilitados.
- Contagem histórica de 92 testes; usar `pytest --collect-only -q` para atualizar após mudanças.

## Arquitetura (o que não é óbvio pelos nomes)

- **Entrypoints**: `src/app.py::main()` para desenvolvimento; `entrypoint.py` é o entry de empacotamento (PyInstaller compila ele e embute `src/extension/` como dado).
- **Pacotes em `src/`**:
  - `core/` — supervisor, heartbeat, buffer circular, resiliência, config, segurança (DPAPI), túnel OpenAI, updater.
  - `mcp/` — `server.py` (JSON-RPC MCP), `ws_bridge.py` (WebSocket **porta 3456**), `router.py` + `schemas_browser.py`/`schemas_computer.py` (namespaces `browser_*` e `computer_*`).
  - `computer/` — mouse/teclado/tela + `safety_gate.py` (**fail-closed / default-deny**) + `kill_switch.py` (3× ESC < 1,2s).
  - `ui/` — painéis CustomTkinter, tray, notificações.
  - `extension/` — MV3 em JS puro (`background/` service worker com triplo keep-alive, `popup/`, `content/`).
- **Portas**: `3456` = bridge local da extensão/MCP WS (dev); `9009` = versão legada portátil. Nunca use 9009 nos testes.
- **`BROWSER-MCP-MTS-PORTATIL/`** é a distribuição legada com `.exe` commitados — não modificar; o cutover/rollback está no README §4.
- Invariante de segurança: toda ação física exige autorização explícita no `SafetyGate`. Nunca tornar `computer_*` default-allow.

## Convenções do repo (diferem do default)

- **Regra de ouro (docs/07): nenhum arquivo passa de 150 LOC** — está sendo cumprida (máx. ~135 em `src/`). Se um arquivo crescer, dividir em sub-módulos.
- Arquivos de teste também < 150 LOC, responsabilidade única; estilo didático com docstrings em pt-BR explicando cada assertiva (TEST_INFRA.md).
- Sem config de lint: siga o estilo existente (docstrings pt-BR, `from __future__ import annotations`, type hints).

## Avisos ao rodar testes

- `tests/conftest.py` tem sentinela de produção: **nunca mate os PIDs em `PROD_PIDS`** (instância de produção legada); a suíte falha se algum morrer durante os testes.
- Use a fixture `dynamic_port` para rede (portas livres), nunca portas fixas.
- Fixtures úteis: `reset_safety_gate`, `process_cleanup_tracker` (sempre limpar processos filhos).

## Git / segredos

- `.gitignore` bloqueia `*runtime-api-key*`, `browser-mts-runtime.yaml`, `.env`, `config/profiles/`, `*.spec`, `dist/`, `build/`, `*.zip` — **nunca commitar segredos**; credenciais usam DPAPI do Windows.
- `.agents/` é gitignored (metadados de orquestração).

## Docs

- `docs/` (pt-BR) é a documentação por tema; **`docs/01` mostra uma árvore TypeScript que não existe** — o código real é Python/JS. Confiar no código, não nessa árvore.
- `README.md` = instalação/uso/troubleshooting; `TEST_INFRA.md` = estratégia e comandos de teste; `CONECTAR_AGENTE_IA.md` = como conectar clientes MCP.

- **Não é PWA**: este projeto é Desktop Python com extensão Manifest V3; não acrescentar Service Worker PWA de site sem requisito.
- **Túnel**: MCP HTTP local 3457; o usuário deve usar um Tunnel ID próprio para evitar conflitos com outras aplicações.
