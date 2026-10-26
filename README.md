# 🌐 NAVEGADOR MTS v2.4.0 — Plataforma Unificada Multi-IA de Automação Web (MV3) e Computer Use para Windows

[![Windows 10 & 11](https://img.shields.io/badge/Windows-10%20%7C%2011%20%7C%20Server%20(64--bit)-blue.svg)](https://microsoft.com/windows)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://python.org)
[![Manifest V3](https://img.shields.io/badge/Chrome%20%26%20Edge-Manifest%20V3-orange.svg)](https://developer.chrome.com/docs/extensions/mv3/intro/)
[![Model Context Protocol](https://img.shields.io/badge/Protocol-MCP%20Multi--IA-purple.svg)](https://modelcontextprotocol.io)
[![Test Suite](https://img.shields.io/badge/Tests-444%2B%20Pytest%20%2B%2029%20Node%20Passing-success.svg)](tests/)

> **NAVEGADOR MTS (v2.4.0)** é uma plataforma desktop universal para **Windows (Windows 10, Windows 11 e Windows Server)** que unifica automação de navegadores (Google Chrome, Microsoft Edge e Chromium via Extensão Manifest V3) e controle seguro do computador (**Computer Use** via Win32/UIA) para **múltiplos agentes de IA simultâneos** (**ChatGPT, Claude Desktop, Claude Code, Google Gemini / Antigravity, OpenCode, Cursor e Codex**).
>
> 🧠 **Cérebro Oficial para Agentes no Obsidian**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\00-INICIO-AQUI.md`

---

## 📸 Demonstração Visual (Fluent Design Dual-Mode: Tema Escuro e Tema Claro)

| Dashboard Fluent (Tema Escuro & Claro) | Painel de Configurações e Conexões Multi-IA |
| :---: | :---: |
| ![Dashboard Dark](docs/screenshots/dashboard_dark.png) | ![Configurações](docs/screenshots/settings_dark.png) |

---

## 🏛️ 1. Arquitetura do Sistema (v2.4.0)

O **NAVEGADOR MTS** foi projetado para permitir que vários agentes de IA operem em paralelo sem conflito de portas, sem roubar o foco do usuário e com segurança física Fail-Closed:

```text
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │   CLIENTES DE IA SIMULTÂNEOS (ChatGPT / Claude / Gemini / OpenCode / Cursor / Codex)│
 └──────────────┬──────────────────────────────┬───────────────────────────┬───────────┘
                │ Stdio (NAVEGADOR_MTS_MCP)    │ HTTP (127.0.0.1:3457/mcp) │ Multi-Túneis
                ▼                              ▼                           ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │                NAVEGADOR MTS CORE (Desktop App Windows 10 / 11)                     │
 │                                                                                     │
 │  ┌────────────────────────┐  ┌────────────────────────┐  ┌───────────────────────┐  │
 │  │ UI Fluent Dual-Mode    │  │ Servidor MCP + Router  │  │ ExecutionCoordinator  │  │
 │  │ Tema Claro/Escuro+Tray │  │ Anti-Forja + Multi-IA  │  │ Locks por Aba / HWND  │  │
 │  └───────────┬────────────┘  └───────────┬────────────┘  └───────────┬───────────┘  │
 └──────────────┼───────────────────────────┼───────────────────────────┼──────────────┘
                │                           │                           │
                ▼                           ▼                           ▼
    ┌───────────────────────┐  ┌─────────────────────────┐  ┌───────────────────────┐
    │ SafetyGate Fail-Closed│  │ WebSocket Bridge Local  │  │ MultiTunnelManager    │
    │ + Kill-Switch 3x ESC  │  │ ws://127.0.0.1:3456..65 │  │ OpenAI + Cloudflared  │
    └───────────┬───────────┘  └────────────┬────────────┘  └───────────────────────┘
                │                           │
                ▼                           ▼
     ┌────────────────────┐     ┌───────────────────────────────────────────────────┐
     │ Windows 10 / 11 OS │     │ Extensão Chrome / Edge (Manifest V3)              │
     │ • Mouse/Teclado    │     │ • Triplo Keep-Alive + Port-Hopping (pula 3457)    │
     │ • Background HWND  │     │ • Auto-Seleção Inteligente + Isolamento por Sessão│
     │ • UIA + Pastas     │     │ • Operação em Segundo Plano (Zero Focus Stealing) │
     └────────────────────┘     └───────────────────────────────────────────────────┘
```

### Principais Pilares da Versão 2.4.0:

1. **Compatibilidade Universal Windows & Interface Dual-Mode (Claro / Escuro)**:
   - Funciona nativamente no **Windows 10, Windows 11 e Windows Server (64-bit)**.
   - Paleta **`FluentPalette` Dual-Mode WCAG AAA** (`src/ui/theme.py`) com suporte completo a **Tema Escuro (`dark`)**, **Tema Claro (`light`)** e **Automático do Sistema (`system`)**, além de efeito Mica opcional no Windows 11.
   - Operação silenciosa na **Bandeja do Sistema (System Tray)** via `pystray` e notificações Toast via `winotify`.

2. **Operação Simultânea Multi-IA e Multi-Túneis**:
   - **Claude Desktop, Claude Code, Google Gemini / Antigravity, OpenCode, Cursor, Codex e ChatGPT** podem trabalhar ao mesmo tempo.
   - **Stdio Inteligente (`HubClient`)**: múltiplos processos `NAVEGADOR_MTS_MCP.exe` detectam o Hub Desktop ativo na porta `3456` e compartilham a ponte sem erro de porta ocupada.
   - **Streamable HTTP (`127.0.0.1:3457/mcp`)**: endpoint HTTP rápido com isolamento por `Mcp-Session-Id`.
   - **`MultiTunnelManager`**: suporta múltiplos túneis simultâneos (`tunnel-client.exe` da OpenAI e `cloudflared.exe` da Cloudflare) apontando para a porta `3457`.
   - **`ExecutionCoordinator`**: locks granulares por aba (`tab:<id>`), por janela (`hwnd:<id>`) e para entrada física (`physical_input`).

3. **Extensão Chrome/Edge Manifest V3 com Auto-Seleção Inteligente**:
   - **Triplo Keep-Alive**: alarmes `chrome.alarms` + ping/pong WebSocket a cada 4s + reconexão com salto automático nas portas `3456..3465` (pulando `3457`).
   - **Auto-Seleção Inteligente de Abas**: resolve automaticamente a aba elegível quando há uma única aba concedida/ativa sem conflito, mantendo isolamento estrito em `chrome.storage.session` quando abas são atribuídas a agentes específicos no popup.
   - **Multi-Navegador**: suporta Chrome e Edge conectados simultaneamente.

4. **Computer Use Avançado (Físico, Background por HWND, UIA e Pastas)**:
   - **Modo Físico e Modo Background**: pode mover o mouse físico com curvas de Bézier ou enviar cliques/teclas diretamente em segundo plano para uma janela (`HWND`) sem mover o cursor do usuário.
   - **Windows UI Automation (UIA)** e **Acesso Confinado a Pastas (`LockedHandle`)** com bloqueio nativo de symlinks, junctions e hardlinks.
   - **Trava `SafetyGate` Fail-Closed (Default-Deny)** e **Kill-Switch Físico Global (`3x ESC` em `< 1,2s`)**.

---

## 🚀 2. Guia de Instalação Passo a Passo

### Pré-requisitos:
- Sistema Operacional: **Windows 10, Windows 11 ou Windows Server (64 bits)**.
- Google Chrome, Microsoft Edge ou navegador Chromium.
- *(Para desenvolvimento)*: **Python 3.10+** e **Node.js 18+**.

---

### 🌟 Opção 1: Instalador Oficial (.exe) em 1 Clique (Recomendado)

1. Execute o arquivo **`dist_installer\NAVEGADOR_MTS_Instalador_v2.4.0.exe`**.
2. O instalador Inno Setup realiza tudo automaticamente (sem exigir privilégios de administrador):
   - Fecha com segurança apenas processos pertencentes à instalação anterior (`installer\close_owned_processes.ps1`).
   - Instala `NAVEGADOR_MTS.exe`, `mcp_stdio\NAVEGADOR_MTS_MCP.exe`, `extension\`, `tunnel-client.exe` e `cloudflared.exe` em `%LOCALAPPDATA%\Programs\Navegador MTS`.
   - Preserva intactos os dados, logs e segredos DPAPI em `%APPDATA%\browser-mcp-mts`.
   - Cria atalhos na Área de Trabalho e no Menu Iniciar.

#### Como atualizar a versão e recompilar o instalador:
```powershell
# 1. Sincronizar versão em src/version.py, src/extension/manifest.json e installer.iss
python release_version.py --set 2.4.0

# 2. Compilar executáveis PyInstaller e instalador Inno Setup 6
.\COMPILAR_INSTALADOR.bat
```

---

### Opção 2: Execução Direta pelo Código-Fonte (Desenvolvedores)

```powershell
pip install -r requirements.txt
python entrypoint.py
```

---

## 🤖 3. Como Conectar Todos os Seus Agentes de IA Simultaneamente

Abra a aba **🤖 Conexões IA** dentro do aplicativo NAVEGADOR MTS para copiar em 1 clique a configuração de qualquer agente, ou utilize os blocos abaixo (veja detalhes completos em [CONECTAR_AGENTE_IA.md](CONECTAR_AGENTE_IA.md)):

### Claude Desktop, Cursor e Google Gemini / Antigravity (Stdio):
```json
{
  "mcpServers": {
    "navegador-mts": {
      "command": "C:\\Users\\SEU_USUARIO\\AppData\\Local\\Programs\\Navegador MTS\\mcp_stdio\\NAVEGADOR_MTS_MCP.exe",
      "args": []
    }
  }
}
```

### Claude Code CLI:
```powershell
claude mcp add navegador-mts "C:\Users\SEU_USUARIO\AppData\Local\Programs\Navegador MTS\mcp_stdio\NAVEGADOR_MTS_MCP.exe"
```

### OpenCode (`opencode.json`):
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "navegador-mts": {
      "type": "local",
      "command": [
        "C:\\Users\\SEU_USUARIO\\AppData\\Local\\Programs\\Navegador MTS\\mcp_stdio\\NAVEGADOR_MTS_MCP.exe"
      ],
      "enabled": true
    }
  }
}
```

### Endpoint HTTP Direto (`127.0.0.1:3457`) e Multi-Túneis (ChatGPT / Cloudflare):
- **Streamable HTTP Local**: `http://127.0.0.1:3457/mcp` (Healthcheck: `http://127.0.0.1:3457/healthz`)
- **WebSocket Bridge Local**: `ws://127.0.0.1:3456`
- **ChatGPT Web**: ative um ou mais túneis no painel do aplicativo e conecte no ChatGPT usando seu Tunnel ID exclusivo.

---

## 🔄 4. Procedimento de Cutover e Rollback (Compatibilidade Legada)

1. A versão moderna opera nas portas **`3456`** (WebSocket) e **`3457`** (HTTP MCP), isolada da versão legada portátil (`9009`).
2. Para carregar a extensão oficial que recebe atualizações automáticas do instalador, carregue sempre a pasta instalada:
   `%LOCALAPPDATA%\Programs\Navegador MTS\extension`
3. Caso precise de rollback imediato para a distribuição portátil v1, encerre o NAVEGADOR MTS pela bandeja do sistema e execute `C:\Users\MATEUS\browser mcp mts\BROWSER-MCP-MTS-PORTATIL\BROWSER MTS.exe`.

---

## 🧪 5. Testes Automatizados e Garantia de Qualidade

O projeto conta com mais de **444 testes Python (`pytest`)** e **29 suítes adversariais em Node.js (`.mjs`)**, mantendo 100% dos arquivos com $\le 150$ linhas de código:

```powershell
# Executar a suíte completa de testes Python:
python -m pytest -q

# Executar a suíte completa de testes da Extensão MV3:
node tests/run_extension_suite.mjs
```

---

## 📄 Licença e Privacidade

Desenvolvido para Windows 10, Windows 11 e Windows Server (64-bit). Operação 100% Local-First com credenciais criptografadas via **Windows DPAPI** em `%APPDATA%\browser-mcp-mts\secrets\`.
