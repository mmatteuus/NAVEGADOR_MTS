# 🤖 Como Conectar o NAVEGADOR MTS (v2.4.0) a Múltiplos Agentes de IA Simultaneamente

O **NAVEGADOR MTS** permite que **ChatGPT, Claude Desktop, Claude Code, Google Gemini / Antigravity, OpenCode, Cursor e Codex** se conectem e operem **ao mesmo tempo** no seu Windows (Windows 10, Windows 11 ou Windows Server).

> 💡 **Dica Rápida:** Dentro do aplicativo desktop **NAVEGADOR MTS**, abra a aba **`🤖 Conexões IA`** para copiar o bloco de configuração já preenchido com o caminho exato do seu usuário Windows!

---

## 1. Arquitetura de Conexão Simultânea

- **Executável MCP Stdio (`NAVEGADOR_MTS_MCP.exe`)**: usado por clientes locais (Claude, Gemini, Antigravity, Cursor, OpenCode, Codex). Quando o aplicativo Desktop já está aberto, cada processo Stdio detecta automaticamente o Hub na porta `3456` (`HubClient`) e compartilha a mesma conexão com o navegador sem conflito de porta!
- **Servidor MCP Streamable HTTP (`http://127.0.0.1:3457/mcp`)**: usado por clientes HTTP diretos e pelos **Multi-Túneis** (OpenAI Secure Tunnel e Cloudflare Quick Tunnel).
- **Coordenador de Execução (`ExecutionCoordinator`)**: garante que múltiplos agentes possam interagir em paralelo em abas ou janelas diferentes sem colisão.

---

## 2. Configuração por Agente de IA

> Substitua `SEU_USUARIO` pelo nome do seu usuário no Windows (ex.: `MATEUS`).

### A. Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`)
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

### B. Claude Code (CLI e Extensão VS Code)
Execute no terminal PowerShell:
```powershell
claude mcp add navegador-mts "C:\Users\SEU_USUARIO\AppData\Local\Programs\Navegador MTS\mcp_stdio\NAVEGADOR_MTS_MCP.exe"
```

### C. Google Gemini CLI / Antigravity (`settings.json` ou `mcp_config.json`)
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

### D. OpenCode (`opencode.json`)
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
*(Ou conecte via Streamable HTTP em `http://127.0.0.1:3457/mcp`).*

### E. Cursor IDE (`~/.cursor/mcp.json`)
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

### F. OpenAI Codex CLI (`~/.codex/config.toml`)
```toml
[mcp_servers.navegador_mts]
command = 'C:\Users\SEU_USUARIO\AppData\Local\Programs\Navegador MTS\mcp_stdio\NAVEGADOR_MTS_MCP.exe'
args = []
```

---

## 3. Conectar com o ChatGPT e Agentes Web (Multi-Túneis)

O **NAVEGADOR MTS v2.4.0** suporta **Multi-Túneis simultâneos** (`MultiTunnelManager`), permitindo manter ativos um ou mais túneis OpenAI (`tunnel-client.exe`) e/ou túneis rápidos Cloudflare (`cloudflared.exe`) apontando para `http://127.0.0.1:3457/mcp`:

1. **Abra o Túnel**: no aplicativo NAVEGADOR MTS, clique em **`🚀 Ligar Túnel ChatGPT`** (ou adicione perfis de túnel adicionais no painel de túneis).
2. **No ChatGPT Web**: abra **Plugins / Conectores MCP** e escolha **Adicionar servidor MCP personalizado**.
3. Preencha os campos:
   - **Nome**: `NAVEGADOR MTS`
   - **Conexão**: Aba **`Túnel`** (para OpenAI Secure Tunnel) informando o seu **Tunnel ID exclusivo**, ou **URL do Servidor** caso utilize um túnel HTTPS Cloudflare.
   - **Autenticação**: **`Sem autenticação`**
4. Aguarde o status **`Pronto (/readyz)`** no aplicativo e teste no chat!

> **Segurança**: As credenciais de runtime do túnel são criptografadas localmente via **Windows DPAPI** em `%APPDATA%\browser-mcp-mts\secrets\`. Nunca cole chaves secretas em arquivos JSON ou no chat.

---

## 4. Segurança e Controle Físico na Sua Mão

- **Auto-Seleção Inteligente e Isolamento de Abas**: Para uso rápido com 1 agente, a extensão seleciona automaticamente a aba elegível. Para uso com múltiplos agentes simultâneos, você pode atribuir abas específicas a cada agente no popup da extensão Chrome/Edge.
- **Trava de Segurança (`SafetyGate` Fail-Closed)**: O agente só consegue usar mouse, teclado ou janelas (`computer_*`) se a chave **"Permitir controle do computador"** estiver ativada no aplicativo.
- **Kill-Switch Físico de Emergência (`3x ESC < 1,2s`)**: Aperte a tecla **`ESC` 3 vezes seguidas** a qualquer momento para cancelar todas as ações na hora e revogar o controle do computador.
