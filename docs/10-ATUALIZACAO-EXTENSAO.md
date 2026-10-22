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
