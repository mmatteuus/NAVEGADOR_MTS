# 🤖 Como Conectar o NAVEGADOR MTS ao seu Agente de IA

O **NAVEGADOR MTS** conecta clientes compatíveis com MCP ao seu navegador. O controle físico do computador exige autorização no aplicativo.

---

## 1. Bloco de Configuração MCP (Model Context Protocol)

Se você utiliza **Claude Desktop**, **Cursor** ou outro cliente MCP compatível, adicione este bloco ao seu arquivo de configuração:

```json
{
  "mcpServers": {
    "browser-mts": {
      "command": "C:\\Users\\SEU_USUARIO\\AppData\\Local\\Programs\\NAVEGADOR MTS\\mcp_stdio\\NAVEGADOR_MTS_MCP.exe",
      "args": []
    }
  }
}
```

> Substitua `SEU_USUARIO` pelo usuário do Windows. Para obter o caminho real, use **Conectar com IA → Copiar Bloco JSON** no aplicativo.

> **Localização do arquivo de configuração do Claude Desktop no Windows:**  
> `%APPDATA%\Claude\claude_desktop_config.json`

> Este aplicativo usa armazenamento local. No fluxo ChatGPT, a credencial é a do Secure Tunnel e deve ser configurada na instalação; ela não é uma chave de API do modelo. Nunca cole credenciais neste arquivo ou no chat.

---

## 2. Conectar com o ChatGPT (Túnel OpenAI)

Para conectar o **ChatGPT** ao seu NAVEGADOR MTS:

1. **Abra o Túnel**: clique no botão **`🚀 Ligar Túnel ChatGPT`** no aplicativo NAVEGADOR MTS (ou execute o arquivo `LIGAR_TUNEL_CHATGPT.bat`).
2. **No ChatGPT Web**: abra **Plugins** e escolha **Adicionar servidor MCP personalizado**.
3. Preencha os campos exatamente assim:
   - **Nome**: `NAVEGADOR MTS`
   - **Conexão**: Clique na aba **`Túnel`** (ao lado de URL do Servidor)
   - **Campo de Conexão**: cole o Tunnel ID próprio gerado para esta instalação. Não use o ID de outra máquina.
   - **Autenticação**: Selecione **`Sem autenticação`**
   - Marque a caixa: ☑️ **Entendo e quero continuar**
   - Clique em: **Criar como plugin**
4. Aguarde o túnel aparecer como pronto no aplicativo. No plugin instalado, clique em **Testar no chat** e peça para abrir uma página de teste e ler seu conteúdo. Uma resposta de `/readyz` sozinha não comprova a conexão completa.
5. Use um Tunnel ID distinto se outra aplicação já utiliza o ID anterior.

> A aba Túnel e a disponibilidade de servidores MCP dependem da conta e da superfície do ChatGPT. Os dados e a configuração ficam na máquina; os resultados das ferramentas solicitadas são enviados ao ChatGPT.

---

## 3. Prompt Pronto para Copiar e Colar no Chat da IA

Copie e cole este texto no início de qualquer conversa com sua IA:

```text
Você é meu assistente de IA conectado ao NAVEGADOR MTS no meu Windows.
O servidor MCP está ativo localmente em ws://127.0.0.1:3456.
Você possui ferramentas disponíveis para:
1. Controle de Navegador (browser_*): navegar em páginas, clicar em botões, preencher formulários, tirar print da tela do browser e ler textos.
2. Controle do Computador (computer_*): quando autorizado por mim no aplicativo, você pode mover o mouse suavemente, clicar e digitar.
Por favor, liste as ferramentas disponíveis e pergunte qual tarefa deseja realizar.
```

---

## 4. Segurança e Controle Físico na sua Mão

- **Trava de Segurança (Fail-Closed):** O agente só consegue mover o mouse ou digitar se o botão *"Permitir controle do computador"* estiver verde no aplicativo desktop.
- **Kill-Switch Físico de Emergência:** Se o agente fizer qualquer movimento indesejado, **aperte a tecla `ESC` 3 vezes seguidas**. Todas as ações são canceladas na hora e o controle é revogado.
- **Botão "Conectar com IA" no App:** Dentro do aplicativo NAVEGADOR MTS, você encontra o botão azul **`🤖 Conectar com IA`** que copia o JSON e permite testar a movimentação visual do mouse com 1 clique!

