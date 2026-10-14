# 🤖 Como Conectar o BROWSER MTS ao seu Agente de IA

O **BROWSER MTS** permite que qualquer IA (Claude, ChatGPT, Cursor ou agentes autônomos) controle seu navegador e seu computador de forma segura e com supervisão total.

---

## 1. Bloco de Configuração MCP (Model Context Protocol)

Se você utiliza **Claude Desktop**, **Cursor** ou outro cliente MCP compatível, adicione este bloco ao seu arquivo de configuração:

```json
{
  "mcpServers": {
    "browser-mts": {
      "command": "C:\\Users\\MATEUS\\AppData\\Local\\Programs\\BROWSER MTS\\BROWSER_MTS.exe",
      "args": ["--stdio"]
    }
  }
}
```

> **Localização do arquivo de configuração do Claude Desktop no Windows:**  
> `%APPDATA%\Claude\claude_desktop_config.json`

---

## 2. Prompt Pronto para Copiar e Colar no Chat da IA

Copie e cole este texto no início de qualquer conversa com sua IA:

```text
Você é meu assistente de IA conectado ao BROWSER MTS no meu Windows.
O servidor MCP está ativo localmente em ws://127.0.0.1:3456.
Você possui ferramentas disponíveis para:
1. Controle de Navegador (browser_*): navegar em páginas, clicar em botões, preencher formulários, tirar print da tela do browser e ler textos.
2. Controle do Computador (computer_*): quando autorizado por mim no aplicativo, você pode mover o mouse suavemente, clicar e digitar.
Por favor, liste as ferramentas disponíveis e pergunte qual tarefa deseja realizar.
```

---

## 3. Segurança e Controle Físico na sua Mão

- **Trava de Segurança (Fail-Closed):** O agente só consegue mover o mouse ou digitar se o botão *"Permitir controle do computador"* estiver verde no aplicativo desktop.
- **Kill-Switch Físico de Emergência:** Se o agente fizer qualquer movimento indesejado, **aperte a tecla `ESC` 3 vezes seguidas**. Todas as ações são canceladas na hora e o controle é revogado.
- **Botão "Conectar com IA" no App:** Dentro do aplicativo BROWSER MTS, você encontra o botão azul **`🤖 Conectar com IA`** que copia o JSON e permite testar a movimentação visual do mouse com 1 clique!

