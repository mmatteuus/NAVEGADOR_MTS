---
name: navegador-mts
description: Guia operacional completo para usar, conectar, configurar e diagnosticar o NAVEGADOR MTS (automação de navegador Chrome/Edge Manifest V3, Computer Use Win32/UIA, Multi-IA simultâneo e Multi-Túneis) em qualquer agente de IA no Windows.
---

# Skill: Operação e Integração Multi-IA do `NAVEGADOR_MTS`

Use esta skill sempre que precisar **operar, conectar, configurar ou diagnosticar** o **NAVEGADOR MTS** (ferramentas `browser_*` e `computer_*`, conexões MCP Stdio/HTTP/WebSocket, túneis para ChatGPT/Cloudflare, extensão Chrome/Edge Manifest V3 ou permissões de segurança).

---

## 1. Cérebro Oficial no Obsidian (Leitura Obrigatória)

Antes de responder dúvidas arquiteturais ou intervir no ecossistema do `NAVEGADOR_MTS`, consulte o cérebro exclusivo do projeto no Obsidian:

- **Ponto de Entrada**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\00-INICIO-AQUI.md`
- **Handoff Vivo (v2.4.0)**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\01-HANDOFF-VIVO.md`
- **Conexões Multi-IA e Túneis**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\04-CONEXOES-MULTI-IA-E-TUNEIS.md`
- **Mapa Forense Discos C: e D:**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\08-MAPA-COMPLETO-DISCOS-C-E-D.md`
- **Consulta rápida via CLI**:
  ```powershell
  node D:\MATEUS\Documentos\GitHub\Obsidian\agent\brain-cli.mjs query "NAVEGADOR_MTS arquitetura multi-ia disco c d"
  ```

> **Regra de Isolamento**: Nunca misture dados, notas ou configurações do `NAVEGADOR_MTS` com `CONSUBOV`, `MARKMAP` ou `MAESTRI`. Nunca registre chaves ou tokens em texto puro.

---

## 2. Mapa Rápido da Máquina (Discos `C:` e `D:`)

| Item | Caminho Canônico |
| :--- | :--- |
| **Repositório Fonte (v2.4.0)** | `D:\MATEUS\Documentos\GitHub\NAVEGADOR_MTS` |
| **App Desktop Instalado** | `C:\Users\MATEUS\AppData\Local\Programs\Navegador MTS\NAVEGADOR_MTS.exe` |
| **Servidor MCP Stdio Instalado** | `C:\Users\MATEUS\AppData\Local\Programs\Navegador MTS\mcp_stdio\NAVEGADOR_MTS_MCP.exe` |
| **Pasta da Extensão Chrome/Edge** | `C:\Users\MATEUS\AppData\Local\Programs\Navegador MTS\extension` |
| **Dados, Logs e DPAPI Secrets** | `C:\Users\MATEUS\AppData\Roaming\browser-mcp-mts` |
| **Porta WebSocket Bridge (Hub)** | `ws://127.0.0.1:3456` (fallback `3458..3465`, pulando `3457`) |
| **Porta MCP Streamable HTTP** | `http://127.0.0.1:3457/mcp` (Healthcheck: `http://127.0.0.1:3457/healthz`) |

---

## 3. Como Conectar Múltiplas IAs Simultaneamente

O `NAVEGADOR_MTS` suporta múltiplos agentes operando **ao mesmo tempo** (`ExecutionCoordinator` + `SessionManager` + `HubClient`):

1. **Claude Desktop / Cursor / Gemini / Antigravity (via Stdio)**:
   ```json
   {
     "mcpServers": {
       "navegador-mts": {
         "command": "C:\\Users\\MATEUS\\AppData\\Local\\Programs\\Navegador MTS\\mcp_stdio\\NAVEGADOR_MTS_MCP.exe",
         "args": []
       }
     }
   }
   ```
   *(Se o Desktop App já estiver aberto na porta `3456`, o `NAVEGADOR_MTS_MCP.exe` detecta o Hub ativo via `hub_client.py` e encaminha as chamadas sem conflito de porta).*

2. **OpenCode (`opencode.json`)**:
   ```json
   {
     "$schema": "https://opencode.ai/config.json",
     "mcp": {
       "navegador-mts": {
         "type": "local",
         "command": [
           "C:\\Users\\MATEUS\\AppData\\Local\\Programs\\Navegador MTS\\mcp_stdio\\NAVEGADOR_MTS_MCP.exe"
         ],
         "enabled": true
       }
     }
   }
   ```

3. **Claude Code CLI**:
   ```powershell
   claude mcp add navegador-mts "C:\Users\MATEUS\AppData\Local\Programs\Navegador MTS\mcp_stdio\NAVEGADOR_MTS_MCP.exe"
   ```

4. **ChatGPT Web e Agentes Remotos (Multi-Túneis)**:
   - O `MultiTunnelManager` permite rodar múltiplos túneis simultâneos (`tunnel-client.exe` da OpenAI ou `cloudflared.exe` da Cloudflare) apontando para `http://127.0.0.1:3457/mcp`.

---

## 4. Uso Correto das Ferramentas MCP (`browser_*` e `computer_*`)

### 4.1. Automação de Navegador (`browser_*`)
- **Abas e Seleção**:
  - Se houver apenas 1 aba atribuída à sua sessão ou 1 aba HTTP/HTTPS elegível em modo de auto-seleção inteligente, o `tabId` é resolvido automaticamente.
  - Se houver múltiplas abas abertas/concedidas, chame primeiro `browser_list_tabs` ou `browser_manage_tabs(action="list")` e informe `tabId` explicitamente nas chamadas subsequentes (`browser_navigate`, `browser_click`, `browser_type`, `browser_get_dom`, `browser_snapshot`, `browser_screenshot`).
- **Zero Focus Stealing**:
  - Prefira operar sem focar a janela do usuário (`active: false` ao abrir abas).

### 4.2. Controle do Computador (`computer_*`)
- **Política Fail-Closed (`SafetyGate`)**:
  - Antes de usar `computer_mouse_action`, `computer_keyboard_action` ou `computer_window_action`, consulte `computer_get_status`.
  - Se `authorized == false`, **peça ao usuário para ativar a chave "Permitir Controle do Computador"** na janela do NAVEGADOR MTS ou no popup da extensão.
  - **Emergência**: O usuário pode abortar qualquer ação física pressionando **`ESC` 3 vezes seguidas em menos de 1,2s** (`EmergencyKillSwitch`).
- **Janelas (`computer_window_action`) e Pastas (`computer_folder_action`)**:
  - Requerem atribuição explícita na aba **Destinos** do aplicativo desktop para a sessão do agente.

---

## 5. Diagnóstico Rápido (Troubleshooting)

- **Erro `EXTENSION_NOT_CONNECTED`**: Verifique se o navegador Chrome/Edge está aberto com a extensão carregada de `C:\Users\MATEUS\AppData\Local\Programs\Navegador MTS\extension` e se o Desktop App está rodando (portas `3456`/`3457`).
- **Erro `BROWSER_SELECTION_REQUIRED` / `TAB_SELECTION_REQUIRED`**: Abra o popup da extensão no navegador e marque a(s) aba(s) desejada(s) ou passe o `tabId` retornado por `browser_list_tabs`.
- **Conflito de Porta `3456` ou `3457`**:
  ```powershell
  Get-NetTCPConnection -LocalPort 3456,3457 -ErrorAction SilentlyContinue | Select-Object LocalPort, State, OwningProcess
  ```
