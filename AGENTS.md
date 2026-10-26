# AGENTS.md

## Cérebro Oficial no Obsidian (Leitura Obrigatória para Agentes)

Antes de iniciar qualquer tarefa de arquitetura, manutenção ou release neste repositório, consulte o cérebro exclusivo do projeto no Obsidian:
- **Ponto de Entrada Obrigatório**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\00-INICIO-AQUI.md`
- **Handoff Vivo (v2.4.0)**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\01-HANDOFF-VIVO.md`
- **Protocolo de Agentes e Release**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\02-PROTOCOLO-PARA-AGENTES.md`
- **Mapa Forense dos Discos C: e D:**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\08-MAPA-COMPLETO-DISCOS-C-E-D.md`
- **Skills Instaladas**: `navegador-mts` (operação/conexão Multi-IA) e `navegador-mts-release` (manutenção, $\le 150$ LOC e compilação de nova versão).

> **Isolamento Estrito**: Nunca misture dados, notas ou configurações do `NAVEGADOR_MTS` com `CONSUBOV`, `MARKMAP` ou `MAESTRI`.

---

## O que é este repo

Aplicativo desktop universal para **Windows (Windows 10, Windows 11 e Windows Server 64-bit)** em Python + CustomTkinter (`FluentPalette` Dual-Mode Claro/Escuro WCAG AAA) que unifica:
1. **Servidor MCP Multi-IA Simultâneo** (Stdio via `NAVEGADOR_MTS_MCP.exe`, Streamable HTTP na porta `3457`, WebSocket Bridge nas portas `3456..3465` pulando `3457` e Multi-Túneis simultâneos para ChatGPT, Claude Desktop/Code, Google Gemini/Antigravity, OpenCode, Cursor e Codex).
2. **Extensão Chrome/Edge Manifest V3** em JavaScript puro (`src/extension/`), com Triplo Keep-Alive, auto-seleção inteligente de abas e isolamento por sessão em `chrome.storage.session`.
3. **Módulo de Computer Use Nativo** (`src/computer/`): mouse/teclado físico e em background por `HWND`, captura multi-monitor DPI-aware, Windows UI Automation (UIA) e acesso confinado a pastas anti-symlink (`LockedHandle`), protegido por `SafetyGate` (**fail-closed / default-deny**) e `EmergencyKillSwitch` (**3× ESC < 1,2s**).

Todo código, comentários e documentação devem estar em **Português do Brasil**.

---

## Comandos (verificados nesta máquina)

```powershell
# Compilação sintática rápida
python -m compileall -q src entrypoint.py stdio_entrypoint.py

# Suíte Python completa (444+ testes unitários, concorrência, segurança e E2E)
python -m pytest -q

# Um módulo específico
python -m pytest tests/test_safety_gate.py -v

# Suíte completa da extensão MV3 em processos Node isolados (requer Node 18+)
node tests/run_extension_suite.mjs

# Rodar o app em desenvolvimento
python entrypoint.py            # UI (flags: --stdio = servidor MCP stdio, --minimized = bandeja)

# Sincronizar versão SemVer (src/version.py, src/extension/manifest.json e installer.iss)
python release_version.py --set 2.4.0
# ou incrementar automaticamente:
python release_version.py --bump patch

# Gerar executáveis PyInstaller + instalador oficial Inno Setup 6
.\COMPILAR_INSTALADOR.bat       # saída em dist_installer\NAVEGADOR_MTS_Instalador_v<VERSAO>.exe
```

- **Regra de Release**: Toda melhoria ou correção funcional deve incrementar a versão (`release_version.py`), passar em 100% dos testes e gerar um novo instalador via `COMPILAR_INSTALADOR.bat`.
- CI de testes e publicação imutável de release: `.github/workflows/windows-qa.yml`.

---

## Arquitetura (o que não é óbvio pelos nomes)

- **Entrypoints**: `src/app.py::main()` para desenvolvimento; `entrypoint.py` gera `NAVEGADOR_MTS.exe` (GUI); `stdio_entrypoint.py` gera `mcp_stdio\NAVEGADOR_MTS_MCP.exe` (console Stdio).
- **Pacotes em `src/`**:
  - `core/` — supervisor, heartbeat, buffer circular, resiliência, config, segurança (DPAPI), `multi_tunnel.py` + `tunnel_service.py` (Multi-Túneis OpenAI e Cloudflare), `updater.py` + `update_web_fallback.py` (fallback contra HTTP 403 do GitHub).
  - `mcp/` — `server.py` (JSON-RPC MCP), `http_server.py` (Streamable HTTP **porta 3457**), `ws_bridge.py` (WebSocket **porta 3456..3465** pulando `3457`), `hub_client.py` (encaminhamento Stdio $\rightarrow$ Hub), `execution_coordinator.py` + `session_manager.py` (locks concorrentes Multi-IA), `router.py` (anti-forja de sessão).
  - `computer/` — mouse/teclado físico e background por `HWND`, UIA (`uia_semantic.py`), pastas (`folder_handles.py`), `safety_gate.py` (**fail-closed / default-deny**) e `kill_switch.py` (**3× ESC < 1,2s**).
  - `ui/` — painéis CustomTkinter com `FluentPalette` Dual-Mode (Claro/Escuro WCAG AAA), `ai_connections_panel.py` / `mcp_copy_dialog.py`, destinos (janelas/pastas), tray e notificações.
  - `extension/` — MV3 em JS puro (`background/` com triplo keep-alive, `tab_access.js` com auto-seleção inteligente e `chrome.storage.session`, `popup/`, `content/`).
- **Portas**: `3456` = bridge local da extensão/MCP WS (`3456..3465` pulando `3457`); `3457` = MCP Streamable HTTP local (`/mcp` e `/healthz`); `9009` = versão legada portátil. Nunca use portas fixas nos testes (use `dynamic_port`).
- **`BROWSER-MCP-MTS-PORTATIL/`** é a distribuição legada com `.exe` commitados — não modificar.
- **Invariante de segurança**: toda ação `computer_*` exige autorização explícita no `SafetyGate`. Nunca tornar `computer_*` default-allow.

---

## Convenções do repo (diferem do default)

- **Regra de ouro (docs/07): nenhum arquivo passa de 150 LOC** — cumprida rigorosamente em 100% de `src/` e `tests/`. Se um arquivo crescer, dividir em sub-módulos.
- Arquivos de teste também $\le 150$ LOC, responsabilidade única; estilo didático com docstrings em pt-BR.
- Siga o estilo existente (docstrings pt-BR, `from __future__ import annotations`, type hints).

---

## Avisos ao rodar testes

- `tests/conftest.py` tem sentinela de produção: **nunca mate os PIDs em `PROD_PIDS`** nem feche processos globais `python.exe` ou `tunnel-client.exe`.
- Use a fixture `dynamic_port` para rede (portas livres), nunca portas fixas.
- Fixtures úteis: `reset_safety_gate`, `process_cleanup_tracker` (sempre limpar processos filhos criados pelo teste).

---

## Git / segredos

- `.gitignore` bloqueia `*runtime-api-key*`, `browser-mts-runtime.yaml`, `.env`, `config/profiles/`, `dist/`, `build/`, `*.zip` — **nunca commitar segredos**; credenciais usam DPAPI do Windows (`%APPDATA%\browser-mcp-mts\secrets\`).
- **Não é PWA**: este projeto é Desktop Python com extensão Manifest V3; não acrescentar Service Worker PWA de site.
