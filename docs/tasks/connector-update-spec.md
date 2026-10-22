# Especificação: conector do navegador e sincronização pós-atualização

Status: SPEC DONE — implementação bloqueada até esta especificação ser aceita pelo
Maestro. Inspeção somente leitura em `main`, HEAD `7fe9e8f`, worktree limpo.

Direção posterior do usuário: publicar a nova versão para teste com seu agente.
O teste do cliente real/recarga é aceite manual do usuário; os gates existentes
de contrato, segurança e extensão permanecem obrigatórios no CI da publicação.

## Objetivo e diagnóstico

Corrigir o uso de uma aba escolhida no popup pelo agente depois da atualização e
garantir que uma atualização do desktop entregue/recarregue a extensão compatível.

Evidência principal: `tab_access.js` grava concessões em
`chrome.storage.session`; porém `targetId(requested, sessionId)` entra no ramo
de sessão e consulta apenas `getTabsForSession(sessionId)`. Abas pré-existentes
liberadas no popup não estão nesse mapa e retornam `TAB_NOT_ALLOWED`. O dispatcher
envia `sessionId` em toda ação MCP, portanto o erro aparece em
`logger.error` (linha 47) como efeito secundário. A imagem não contém a mensagem
original, logo não se deve afirmar outra causa sem reprodução.

Risco relacionado: `ws_session_registry.py` tem fallback para a extensão ativa
quando não há socket específico; isso deve permanecer apenas para roteamento,
sem conceder acesso a abas. `SafetyGate` e a seleção explícita de abas são
invariantes.

## Contrato requerido

1. O popup continua sendo o único concedente; somente URLs HTTP/HTTPS podem ser
   concedidas; `storage.session` permanece a fonte de concessões do navegador.
2. Com `tabId` explícito, a extensão aceita a aba se ela estiver concedida e não
   tiver outro proprietário. Se a sessão ainda não a possuir, a associação deve
   ser feita atomicamente antes da ação; outra sessão recebe
   `TAB_ACCESS_DENIED`.
3. Sem `tabId`, uma sessão pode usar somente sua única aba associada ou, quando
   ainda não possui associação, a única concessão global; múltiplas concessões
   retornam `TAB_SELECTION_REQUIRED`. Nunca consultar aba ativa como fallback.
4. Fechamento, troca/reuso de ID, desconexão ou limpeza revogam a associação;
   `browser_new_tab` continua sem concessão silenciosa, salvo a regra explícita
   já existente para criação feita pela ação autorizada.
5. Toda falha de seleção deve atravessar `buildActionResponse` preservando o
   código estável e a mensagem útil para o agente; logger deve incluir ação,
   `tabId`, `sessionId` e código sem registrar segredos.
6. O instalador versionado deve copiar `src/extension`; no handshake, a extensão
   anuncia `chrome.runtime.getManifest().version`, o desktop compara com
   `APP_VERSION` e pede uma única recarga quando a extensão é antiga. A política
   não pode recarregar em loop nem declarar atualização quando não há asset
   instalador validado.

## Grafo de implementação

**CONN-1 (tab authorization):** ajustar `tab_access.js`/`session_registry.js`
para validar concessão global e vincular a sessão de forma serializada; manter
`validateTabAccess` fail-closed e todos os caminhos `browser_*` sob `requireGranted`.

**CONN-2 (server contract):** adicionar/ajustar testes do fluxo MCP com
`sessionId`, uma e várias concessões, concorrência entre sessões, aba fechada e
ID reutilizado. Não alterar o fallback de socket para autorização.

**UPD-1 (sync):** conferir handshake, cópia no instalador e recarga única;
adicionar teste de versão antiga, igual, nova, versão ausente e reconexão após
reload. Se a extensão estiver carregada de outra pasta, reportar como
`BLOCKED`/manual; não sobrescrever instalação externa.

**QA-1 (independente):** executar suíte Python, testes Node da extensão e E2E
real Chrome/Edge com popup, duas abas e agente com `sessionId`; registrar SHA,
ambiente, dirty state, logs e resultado. Revisar segurança e LOC (<150 por arquivo).

**REL-1 (release):** somente após QA, atualizar versão canônica de `main`, gerar
instalador full versionado, checksum e release. Push/ publicação exigem gate do
Maestro; não modificar `BROWSER-MCP-MTS-PORTATIL`.

## Aceitação, riscos e parada

Aceitar somente se uma aba escolhida no popup for usada pelo agente com
`tabId` explícito, sem seleção ativa implícita; duas sessões não compartilham a
mesma aba; a suíte e E2E real passam; e uma instalação atualizada recarrega a
extensão empacotada na mesma versão. Falhar fechado em concessão ausente,
sessão desconhecida, URL proibida, erro de checksum, asset ausente ou divergência
de versão. Parar antes de push se houver diff não compreendido, teste falho,
segredo, runner/credencial indisponível ou ausência de evidência remota do asset.
