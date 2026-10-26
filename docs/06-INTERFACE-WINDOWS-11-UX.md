# 🎨 06. Interface Gráfica Universal (Windows 10 / 11), Temas Claro/Escuro e UX (v2.4.0)

## 1. Compatibilidade Universal Windows e Design Fluent Dual-Mode

O **NAVEGADOR MTS v2.4.0** funciona nativamente em **qualquer versão moderna do Windows 64-bit (Windows 10, Windows 11 e Windows Server)**, seguindo os princípios do **Microsoft Fluent Design System** através do `CustomTkinter` (`src/ui/theme.py`):

- **Paleta `FluentPalette` Dual-Mode WCAG AAA**:
  - Suporte completo e instantâneo a **Tema Escuro (`dark`)**, **Tema Claro (`light`)** e **Automático do Sistema (`system`)**.
  - Cores semânticas de alto contraste:
    - **Fundo Principal**: `#141416` (Escuro) / `#F3F3F5` (Claro)
    - **Cartões Elevados**: `#1E1E22` (Escuro) / `#FFFFFF` (Claro)
    - **Bordas**: `#2B2B33` (Escuro) / `#E5E5EB` (Claro)
    - **Texto Principal**: `#FFFFFF` (Escuro) / `#1A1A1A` (Claro) — contraste WCAG AAA.
- **Efeito Mica Defensivo**: No Windows 11, aplica o backdrop Mica (`DwmSetWindowAttribute` atributo 38 / `pywinstyles`). No Windows 10 ou Windows Server, utiliza fallback sólido elegante sem qualquer erro ou perda de funcionalidade.

---

## 2. Layout Moderno com Barra Lateral e Painel Multi-IA

A janela principal (`src/ui/main_window.py`) conta com barra lateral de navegação dividida em 4 áreas principais e seletor rápido de Tema (Claro / Escuro / Sistema):

```text
+------------------------------------------------------------------------------------+
| 🌐 NAVEGADOR MTS v2.4.0                        [🌓 Tema: Escuro/Claro] [—] [□] [X] |
+----------------------+-------------------------------------------------------------+
| 🧭 NAVEGAÇÃO         | 📊 DASHBOARD EM TEMPO REAL                                  |
|                      |                                                             |
| [ 📊 Dashboard     ] |  +---------------------------+ +--------------------------+ |
| [ 🤖 Conexões IA   ] |  | 🔌 Servidor MCP & HTTP    | | 🌐 Extensão Chrome/Edge  | |
| [ 🎯 Destinos      ] |  | WS: 3456 | HTTP: 3457     | | Status: Conectada        | |
| [ ⚙️ Configurações ] |  | Túneis Ativos: Prontos    | | Latência: 12ms           | |
|                      |  +---------------------------+ +--------------------------+ |
|                      |                                                             |
|                      |  +--------------------------------------------------------+ |
|                      |  | 🛡️ CONTROLE DO COMPUTADOR (SAFETY GATE FAIL-CLOSED)    | |
|                      |  | Permissão de mouse, teclado e janelas: [ LIGADO (ON) ] | |
|                      |  | 🚨 Kill-Switch Físico: Pressione ESC 3x (< 1,2s)       | |
|                      |  +--------------------------------------------------------+ |
|                      |                                                             |
| [ 🔄 Atualizações  ] |  +--------------------------------------------------------+ |
|                      |  | 📋 Console de Eventos e Diagnóstico                    | |
+----------------------+-------------------------------------------------------------+
```

### Painéis Especializados da UI (`src/ui/`):
1. **`DashboardPanel` (`dashboard_panel.py`)**: Telemetria em tempo real (status do MCP, porta WebSocket ativa, latência, status dos túneis, chave mestra do `SafetyGate` e console de logs sanitizados).
2. **`AIConnectionsPanel` / `MCPCopyDialog` (`ai_connections_panel.py` / `mcp_copy_dialog.py`)**: Central de **Conexões Multi-IA** para copiar em 1 clique a configuração de **ChatGPT, Claude Desktop, Claude Code, Google Gemini / Antigravity, OpenCode, Cursor e Codex**, além de controlar múltiplos túneis simultâneos.
3. **`DestinationsPanel` (`destinations_panel.py`, `window_assignment_panel.py`, `folder_assignment_panel.py`)**: Permite atribuir ou revogar janelas (`HWND`) e pastas locais para cada sessão de agente conectada.
4. **`SettingsPanel` (`settings_panel.py`)**: Gerenciamento seguro de credenciais DPAPI, inicialização automática com o Windows (`autostart.py`) e diagnóstico.

---

## 3. Integração com a Bandeja do Sistema (System Tray)

1. **Segundo Plano Permanente ao Clicar no 'X'**: Fechar a janela principal apenas a oculta para a bandeja do sistema (`pystray`), mantendo o servidor MCP, os túneis e a ponte WebSocket 100% operacionais.
2. **Encerramento Explícito**: Para encerrar completamente o aplicativo, utilize a opção **"❌ Sair do Aplicativo"** no menu de contexto do ícone na bandeja do Windows.
3. **Semáforo Visual no Ícone da Bandeja**:
   - 🟢 **Verde (`#107C41`)**: Extensão conectada e serviços ativos.
   - 🟠 **Laranja (`#D83B01`)**: Aguardando conexão da extensão do navegador.
   - 🔴 **Vermelho (`#D13438`)**: Serviços pausados ou erro.
