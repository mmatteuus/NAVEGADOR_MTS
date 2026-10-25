# Atualização do conector e escolha de abas

O aplicativo consulta a release oficial ao iniciar e periodicamente. Ao aceitar
a atualização no aplicativo, o instalador completo substitui também a pasta
`extension` dentro da instalação. O navegador recebe uma solicitação de recarga
quando a extensão anuncia uma versão anterior à do aplicativo.

Carregue a extensão Chrome/Edge usando a pasta `extension` da instalação do
NAVEGADOR MTS. O atalho “Pasta da Extensao Chrome” no menu Iniciar aponta para
essa pasta. Uma cópia extraída em outro local não recebe os arquivos do instalador:
nesse caso, carregue a pasta instalada uma vez para acompanhar as próximas versões.

Depois de recarregar/atualizar a extensão ou reiniciar o navegador, abra seu popup,
selecione as abas permitidas e salve. As concessões ficam apenas na sessão do
navegador; não concedemos acesso permanente com base em IDs antigos.

Uma aba concedida pode ser associada a uma sessão de agente. Outra sessão não
pode usá-la enquanto estiver associada. Com várias abas permitidas, informe
`tabId` na ferramenta; com uma única aba disponível a escolha é inequívoca.
Limpar ou desmarcar uma concessão revoga o acesso concedido pelo popup.

Ao usar Chrome e Edge ao mesmo tempo, selecione as abas no navegador desejado.
Se a seleção permanecer ambígua, o conector solicita uma escolha em vez de
encaminhar uma ação para outro navegador. A sessão permanece no navegador
escolhido mesmo durante uma desconexão temporária.

Para diagnosticar um erro, copie a mensagem acima de “Contexto” no painel de
erros da extensão. `common/logger.js:47` identifica o registro do erro, enquanto
a mensagem contém sua causa (por exemplo, seleção ou autorização de aba).

As garantias da API estão documentadas pelo Chrome em
[runtime.reload](https://developer.chrome.com/docs/extensions/reference/api/runtime#method-reload)
e [storage.session](https://developer.chrome.com/docs/extensions/reference/api/storage#property-session).

## Recarga após atualização

O Service Worker guarda em `chrome.storage.local` o estado da atualização
(`browser_mts_extension_update_state`). Para cada versão alvo, a recarga é
solicitada uma única vez. Se houver comandos em execução, o pedido fica
pendente até a fila sinalizar que está livre; isso evita invalidar um contexto
de conteúdo no meio de uma ação.

Depois da recarga, o próximo `client_hello` deve confirmar a versão real do
manifesto. Uma versão ainda antiga produz o estado `error` e aparece no popup
para diagnóstico. Uma cópia carregada de outra pasta não recebe os arquivos do
instalador: nesse caso o diagnóstico permanece explícito e não há loop de
recargas. Para atualização automática, mantenha a extensão carregada da pasta
`extension` da instalação do aplicativo.

### Evidência de QA

No perfil Chromium descartável de QA, o modo de desenvolvedor foi habilitado
somente nesse perfil por `chrome.developerPrivate.updateProfileConfiguration`.
O E2E então substituiu a versão `2.2.0` pela versão do manifesto `2.3.2`,
observou o novo Service Worker com `onInstalled: update`, e confirmou o fluxo
de atribuição explícita: AgentA executou a ação, AgentB recebeu
`TAB_ACCESS_DENIED`, e a revogação foi respeitada. Isso valida o mecanismo no
perfil de teste; não declara que o navegador do usuário já está instalado ou
atualizado.
