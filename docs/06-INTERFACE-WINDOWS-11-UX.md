# 🎨 06. Interface Windows 11 e Experiência do Usuário (UX)

## 1. Diretrizes de Design do Windows 11

O novo **BROWSER MTS** foi idealizado para ter a aparência e a sensação de um aplicativo nativo moderno do Windows 11, seguindo os princípios de design da Microsoft (**Fluent Design System**):

- **Tipografia**: Uso da fonte padrão do sistema, `Segoe UI Variable`.
- **Bordas e Cantos**: Cantos suavemente arredondados (`border-radius: 8px` a `12px`).
- **Paleta de Cores e Temas**: Suporte total a **Tema Escuro (Dark Mode)** e **Tema Claro (Light Mode)** com adaptação automática ao tema do Windows.
- **Efeito Visual**: Transparências sutis estilo Mica/Acrílico com elevação por sombras suaves.

---

## 2. Layout do Painel Principal (Dashboard)

A tela principal do aplicativo é limpa, intuitiva e focada na observabilidade em tempo real:

```text
+------------------------------------------------------------------------+
| 🌐 BROWSER MTS & COMPUTER USE                       [⚙️ Config] [—] [X] |
+------------------------------------------------------------------------+
|                                                                        |
|  [ 🟢 SISTEMA OPERACIONAL & ONLINE ]                  Versão: 2.0.0    |
|                                                                        |
|  +------------------------+  +------------------------+                |
|  | 🔌 Servidor MCP        |  | 🌐 Extensão Chrome     |                |
|  | Status: Conectado      |  | Status: Conectada      |                |
|  | Túnel: OpenAI Secure   |  | Aba: github.com/mateus |                |
|  | Latência: 24ms         |  | Porta: 3456            |                |
|  +------------------------+  +------------------------+                |
|                                                                        |
|  +------------------------------------------------------------------+  |
|  | 🛡️ CONTROLE DO COMPUTADOR (COMPUTER USE)                         |  |
|  |                                                                  |  |
|  | Permissão de mouse, teclado e tela: [  LIGADO (ON)  ]  (Toggle)  |  |
|  |                                                                  |  |
|  | Status: 🟢 O Agente PODE interagir com o computador               |  |
|  | 🚨 Kill-Switch de Emergência: Pressione ESC 3x para interromper  |  |
|  +------------------------------------------------------------------+  |
|                                                                        |
|  +------------------------------------------------------------------+  |
|  | 📋 Registro de Atividades em Tempo Real (Logs de Diagnóstico)     |  |
|  | [12:04:12] Conexão WebSocket estabelecida com extensão Chrome     |  |
|  | [12:04:15] Ferramenta executada: browser_navigate (sucesso)       |  |
|  | [12:04:18] Heartbeat OK (latência: 12ms)                          |  |
|  |                                               [Limpar] [Copiar]  |  |
|  +------------------------------------------------------------------+  |
|                                                                        |
+------------------------------------------------------------------------+
```

---

## 3. Integração com a Bandeja do Sistema (System Tray)

Para garantir uso prático no dia a dia ("zero cliques"), o aplicativo roda em segundo plano sem poluir a barra de tarefas:

1. **O botão 'X' apenas oculta a janela (Segundo Plano Permanente)**: Ao clicar no botão 'X' superior, a janela é ocultada imediatamente, mas todo o processamento de segundo plano (servidor MCP, ponte WebSocket com a extensão e listeners de segurança) continua 100% ativo e operacional.
2. **Encerramento Exclusivo pela Bandeja**: Para fechar e desativar o aplicativo por completo, o usuário deve obrigatoriamente clicar com o botão direito no ícone da bandeja do sistema (junto ao relógio do Windows) e escolher a opção **'❌ Sair do Aplicativo'**.
3. **Ícone Dinâmico de Status**:
   - 🟢 **Verde**: Todos os serviços ativos, extensão conectada e operacional.
   - 🟡 **Amarelo**: Tentando reconectar extensão ou aguardando conexão.
   - 🔴 **Vermelho**: Serviços pausados ou erro de rede.
4. **Menu de Contexto com Botão Direito**:
   - 🌐 Abrir BROWSER MTS (ou duplo-clique no ícone para restaurar a janela)
   - 🛡️ Alternar Trava Computer Use (Ativado / Desativado)
   - 🔌 Alternar Servidor MCP
   - ❌ Sair do Aplicativo (Encerramento real)

---

## 4. Notificações Nativas do Windows (Toast Notifications)

O sistema utiliza notificações nativas do Windows para comunicar eventos cruciais de forma discreta:
- **Alerta de Emergência**: Quando o Kill-Switch é pressionado, uma notificação imediata confirma a revogação do controle.
- **Queda e Restauração de Conexão**: Se a internet ou o navegador oscilar, o usuário é notificado apenas se a queda persistir por mais de 10 segundos, evitando avisos falsos durante reconexões normais de 1 segundo.

---

## 5. Próximo Documento

Para conhecer as regras de código limpo, arquitetura em arquivos pequenos e padrões de modularidade:
👉 **[07. Guia de Código e Boas Práticas](07-GUIA-DE-MODULARIDADE-E-BOAS-PRATICAS.md)**

