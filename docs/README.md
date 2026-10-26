# 🌐 NAVEGADOR MTS & COMPUTER USE (v2.4.0) — Documentação Oficial do Sistema

> **Visão Geral**: Plataforma desktop universal para **Windows (Windows 10, Windows 11 e Windows Server 64-bit)** com design Fluent Dual-Mode (Tema Claro e Tema Escuro WCAG AAA), combinando automação de navegadores via extensão Chrome/Edge Manifest V3, suporte simultâneo **Multi-IA e Multi-Túneis**, e automação segura do computador (mouse, teclado, tela, janelas UIA e pastas) protegida por trava Fail-Closed (`SafetyGate`) e Kill-Switch de emergência (`3x ESC < 1,2s`).
>
> 🧠 **Cérebro Oficial para Agentes no Obsidian**: `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\00-INICIO-AQUI.md`

---

## 📚 Índice da Documentação

| Documento | Assunto Principal | Conteúdo Abordado |
| :--- | :--- | :--- |
| **[01. Visão Geral e Arquitetura](01-VISAO-GERAL-E-ARQUITETURA.md)** | Arquitetura Real v2.4.0 | Estrutura modular em Python + JS MV3, fluxo Multi-IA e componentes. |
| **[02. Resiliência e Reconexão](02-RESILIENCIA-E-RECONEXAO.md)** | Diagnóstico e Auto-Cura | Motor de resiliência de 5 camadas, heartbeat e recuperação em $\le 5\text{s}$. |
| **[03. Extensão do Navegador](03-EXTENSAO-NAVEGADOR.md)** | Extensão Manifest V3 | Service worker, port-hopping (`3456..3465` pulando `3457`), auto-seleção de abas e `chrome.storage.session`. |
| **[04. Automação do Computador](04-CONTROLE-COMPUTADOR-COMPUTER-USE.md)** | Computer Use & Segurança | Mouse/teclado físico e background por `HWND`, UIA, pastas e Kill-Switch. |
| **[05. Servidor MCP e Transporte](05-SERVIDOR-MCP-E-TRANSPORTE.md)** | Multi-IA e Multi-Túneis | Transportes Stdio (`HubClient`), HTTP (`:3457`), WS (`:3456`), `ExecutionCoordinator` e `MultiTunnelManager`. |
| **[06. Interface Windows e Temas](06-INTERFACE-WINDOWS-11-UX.md)** | UI Fluent Claro/Escuro | `FluentPalette` Dual-Mode WCAG AAA, painel Multi-IA, System Tray e suporte Windows 10/11. |
| **[07. Guia de Modularidade e Boas Práticas](07-GUIA-DE-MODULARIDADE-E-BOAS-PRATICAS.md)** | Padrões de Engenharia | Regra inegociável de $\le 150$ linhas por arquivo (LOC), padrões Python/JS e release versionado. |
| **[08. Armazenamento Local e Privacidade](08-ARMAZENAMENTO-LOCAL-E-PRIVACIDADE.md)** | Privacidade e DPAPI | Política 100% Local-First, criptografia Windows DPAPI e mascaramento de logs. |
| **[09. Testes de Integração Windows](09-TESTES-INTEGRACAO-WINDOWS.md)** | Validação Integrada | Scripts e verificações de contrato no Windows. |
| **[10. Atualização da Extensão e Abas](10-ATUALIZACAO-EXTENSAO.md)** | Ciclo MV3 e Concessões | Auto-reload coordenado da extensão, seleção inteligente e isolamento multi-navegador. |
| **[11. Destinos por Agente](11-DESTINOS-POR-AGENTE.md)** | Isolamento Multi-Agente | Concessão de abas web, janelas Win32/UIA e pastas locais por sessão de IA. |
| **[Atualizações e Releases](atualizacoes.md)** | Auto-Update e Build | Fluxo `release_version.py`, `COMPILAR_INSTALADOR.bat`, fallback web anti-403 e CI GitHub Actions. |

---

## 🎯 Princípios Fundamentais do Projeto

1. **Arquitetura em Arquivos Pequenos ($\le 150$ LOC)**: Nenhum arquivo em `src/` ou `tests/` ultrapassa 150 linhas.
2. **Operação Multi-IA Simultânea**: ChatGPT, Claude, Gemini/Antigravity, OpenCode, Cursor e Codex operam juntos sem conflito.
3. **Segurança Fail-Closed (`SafetyGate`)**: O agente nunca controla o sistema operacional sem autorização explícita do usuário.
4. **Compatibilidade Universal Windows**: Funciona perfeitamente no Windows 10, Windows 11 e Windows Server com Tema Claro e Tema Escuro.
5. **Versionamento Estrito**: Toda melhoria gera uma nova versão sincronizada e um novo instalador `.exe`.
