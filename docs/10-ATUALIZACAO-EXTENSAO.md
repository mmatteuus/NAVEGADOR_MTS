# 🔄 10. Atualização da Extensão, Auto-Seleção Inteligente e Isolamento de Abas (v2.4.0)

## 1. Carregamento Oficial e Atualização Automática da Extensão

O aplicativo desktop consulta a release oficial ao iniciar e periodicamente. Ao instalar uma nova versão pelo instalador completo (`NAVEGADOR_MTS_Instalador_v2.4.0.exe`), a pasta `extension` dentro de `%LOCALAPPDATA%\Programs\Navegador MTS\extension` também é atualizada automaticamente.

- **Regra Fundamental**: Carregue sempre a extensão no Google Chrome (`chrome://extensions`) e no Microsoft Edge (`edge://extensions`) apontando para a pasta instalada:
  `C:\Users\MATEUS\AppData\Local\Programs\Navegador MTS\extension`
  *(O atalho "Pasta da Extensão Chrome" no Menu Iniciar e na Área de Trabalho aponta diretamente para esse diretório).*
- Quando o aplicativo desktop detecta no handshake WebSocket (`client_hello`) que a extensão está em uma versão anterior à `APP_VERSION` (`2.4.0`), ele envia um comando coordenado de recarga (`reload_extension`).

---

## 2. Seleção de Abas: Auto-Seleção Inteligente vs. Isolamento Multi-Agente

O módulo `src/extension/background/tab_access.js` opera em dois modos complementares:

### A. Auto-Seleção Inteligente (Zero Fricção para Fluxo Rápido)
- Quando há apenas **1 aba atribuída à sessão** do agente ou **1 aba livre elegível (`http://` ou `https://`)** sem conflito com outros agentes, a extensão resolve e seleciona a aba automaticamente mesmo que o agente não informe `tabId`.
- Isso elimina bloqueios desnecessários de `TAB_SELECTION_REQUIRED` quando o usuário está utilizando um único agente.

### B. Atribuição Explícita por Agente no Popup (Multi-IA Simultâneo)
- Quando múltiplos agentes estão conectados simultaneamente (ex.: Claude Desktop + ChatGPT + OpenCode), você pode abrir o Popup da extensão, marcar as abas permitidas e associar cada aba a um agente específico (`sessionId`).
- As concessões e vínculos de posse ficam salvos em **`chrome.storage.session`** (`browser_mts_session_tab_grants` e `browser_mts_popup_tab_owners`), sobrevivendo ao ciclo de suspensão do Service Worker MV3 durante toda a sessão do navegador.
- Outra sessão de agente não pode interagir com uma aba atribuída a um agente diferente (`TAB_ACCESS_DENIED`).
- Limpar ou desmarcar uma concessão no popup revoga o acesso imediatamente.

---

## 3. Uso Simultâneo de Múltiplos Navegadores (Chrome + Edge)

- O `WSSessionRegistry` (`src/mcp/ws_session_registry.py`) permite que o Google Chrome e o Microsoft Edge estejam conectados ao mesmo tempo na porta `3456`.
- Os comandos de cada sessão são roteados deterministicamente para o navegador onde a aba daquela sessão está aberta e concedida.

---

## 4. Mecanismo Seguro de Recarga Pós-Atualização (`ws_update.js`)

O Service Worker guarda em `chrome.storage.local` o estado da atualização (`browser_mts_extension_update_state`). Para cada versão alvo:
1. A recarga (`chrome.runtime.reload()`) é solicitada uma única vez.
2. Se houver comandos `browser_*` em execução na fila (`session_queues.js`), o pedido de recarga aguarda até a fila ficar ociosa (`getActiveQueueCount() === 0`), evitando interromper um clique ou extração de DOM pela metade.
3. Após a recarga, o novo `client_hello` confirma a versão atualizada do `manifest.json`.
