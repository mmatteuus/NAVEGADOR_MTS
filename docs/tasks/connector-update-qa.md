# QA independente: conector e atualização

Data: 2026-10-22 (America/Sao_Paulo)
SHA: `7fe9e8fdcce340c4ac5d0f04c677d32d61dbecef`
Branch: `main`; estado inicial: `docs/tasks/connector-update-spec.md` não rastreado.

## Proteções verificadas

- `tests/conftest.py` protege `PROD_PIDS = [17892, 8928, 6548, 6052]`, usa
  `dynamic_port` e mata somente processos registrados em `process_cleanup_tracker`.
- No início, nenhum dos quatro PIDs estava vivo (`prod_alive=[]`). Nenhum
  processo foi encerrado por esta QA.
- O E2E real usa perfis temporários em `temp/e2e-real/profile_*` e copia a
  extensão para `temp/e2e-real/ext_*`; não usa o perfil pessoal do navegador.

## Linha de base

| Comando | Resultado |
|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | BLOQUEADO: `.venv` não existe |
| `python -m pytest -q` | BLOQUEADO na coleta: 29 diretórios sob `temp/` deram `WinError 5` |
| `python -m pytest tests -q` | `254 passed, 5 failed, 35 errors` em 44,31 s |
| `node tests/test_extension_adversarial.mjs` | PASS: 4 cenários adversariais |
| `node tests/e2e_real/test_e2e_real_multisession.mjs` | BLOQUEADO em sandbox (`spawn EPERM`); com escalada iniciou bridge/Chromium, mas não reconectou a extensão em 15 s |
| `QA_RUN_REAL_E2E=1 node tests/e2e_real/test_connector_popup_update.mjs` | BLOQUEADO com escalada: Chromium iniciou, mas a extensão não apareceu como conectada em 10 s; módulo Playwright global foi localizado |

Após escalada, a suíte direcionada (`python -m pytest tests -q
--basetemp=temp/qa-connector-231`) terminou em `293 passed, 3 failed` em
162,12 s. As três falhas foram: cursor físico movido por teste de coordenadas
anômalas, `ws_client.js` ainda com 150 linhas (o teste exige `<150`) e timeout
do E2E multissessão real. Isso é evidência atual do checkout, não aprovação.

Diagnóstico do novo E2E com logs do worker: a cópia carregou a porta correta
(`ws://127.0.0.1:62969`), conectou e recebeu `server_hello` com desktop `2.3.1`.
Como o worker iniciou com versão antiga, recebeu `reloadRequired` e fechou. A
alteração de `manifest.json` em disco enquanto a extensão estava carregada fez
o popup seguinte retornar `ERR_BLOCKED_BY_CLIENT`; o Chromium não reinstanciou
uma extensão unpacked com manifesto alterado. Portanto o fluxo precisa simular
a troca pelo instalador/reload em diretório compatível, sem editar o manifesto
de uma extensão carregada. O E2E permanece BLOCKED até essa fixture ser corrigida.

O teste isolado de coordenadas extremas foi repetido e passou: `1 passed in
0,27 s`; a falha ampla de cursor é intermitente e não foi reproduzida nessa
execução independente.

Falhas de código observadas na baseline: `src/extension/background/ws_client.js`
tem 156 linhas (limite do projeto: 150), causando três testes de LOC. O teste
de port hopping falhou com `WinError 10013` ao tentar bindar portas dinâmicas.
Os 35 erros restantes são predominantemente `PermissionError` ao criar
`tmp_path` em `C:\Users\MATEUS\AppData\Local\Temp\pytest-of-MATEUS` e não
constituem evidência de regressão do conector.

## Critérios mínimos para a próxima QA

- Reexecutar a suíte com `.venv` válido ou ambiente Python explicitamente
  autorizado e diretórios temporários graváveis.
- Reexecutar o E2E real com permissão para `spawn`, perfil descartável e bridge
  em porta dinâmica.
- Adicionar/revisar casos para uma aba concedida com `tabId` e `sessionId`,
  duas sessões concorrentes, aba fechada/reutilizada e sincronização de versão
  da extensão após atualização do instalador.

Foi adicionado somente o teste independente `tests/e2e_real/test_connector_popup_update.mjs`
(96 LOC; `node --check` passou); nenhum arquivo de produto foi alterado por esta QA.

QA final após build: `python -m pytest tests -q --basetemp=temp/qa-connector-final-231
--junitxml=temp/connector-final-tests.xml` terminou em `300 passed, 2 failed`
em 163,80 s. A falha de stress foi de contrato textual: esperava `não conectada`,
mas recebeu `EXTENSION_NOT_CONNECTED: extensão compatível não identificada.`.
O runner Python do E2E atingiu timeout de 90 s, embora a mesma suíte real
executada diretamente com Playwright global tenha passado nos cinco cenários.

Fingerprint independente informado após o build: SHA-256 dos 94 arquivos de
produto `68b943961fe30a8b6e86558d608d68fe637459a1e96c88a966a8fac00502fe2e`;
HEAD `7fe9e8f` com diff de trabalho dos agentes. Node runner: 16 testes PASS;
smoke MCP: versão `2.3.1`, 15 ferramentas, exit 0.

Após a correção localizada da mensagem de compatibilidade, o fingerprint novo
dos mesmos 94 arquivos é `3a5ed105bb2da00f25cabc0a658fbfca186081e9b32dc721ef76e0a96ffef168`.
Os resultados anteriores devem ser associados ao fingerprint `68b9...fe2e`;
o novo checkout exige nova rodada final.

O wrapper Python foi ajustado para passar `PLAYWRIGHT_MODULE` absoluto do
Playwright global e `QA_PYTHON=sys.executable`. Isoladamente, passou em
`1 passed` em 68,13 s. Na suíte completa seguinte (`299 passed, 3 failed`), o
runner falhou antes do Chromium, com `Timeout iniciando fixture_mcp_bridge.py`
em 15 s; isso ocorreu sob concorrência dos demais testes/processos e não é a
mesma falha do E2E direto, que passou.

As outras duas falhas foram instabilidades de ambiente: o sampler detectou
desvio físico do cursor `(-171, 524)` durante ações virtuais, e o supervisor
ainda reportou o processo morto como vivo após 100 ms. Ambas exigem reteste
isolado antes de atribuir regressão ao conector.

O workflow agora possui o job `e2e_conector` em Windows descartável. Ele instala
Playwright `1.63.0` em `temp/qa-node`, baixa Chromium, define `PLAYWRIGHT_MODULE`,
`QA_PYTHON` e `QA_RUN_REAL_E2E=1`, executa o novo E2E e publica somente
`temp/connector-e2e.log` como artefato textual. Esse diagnóstico é manual
(`workflow_dispatch`); contratos/segurança e Node permanecem gates da release.

Após o instalador terminar, os checks direcionados passaram: desconexão
`test_stress_abrupt_extension_disconnect_inflight` (`1 passed`, 0,64 s) e
`test_process_death_and_auto_restart` (`1 passed`, 2,64 s). O wrapper Python do
E2E continuou intermitente: em uma rodada expirou em 90 s; em diagnóstico com
captura de saída iniciou bridge e dois contextos, mas a extensão não conectou
em 15 s. O E2E direto já havia passado nos cinco cenários em rodada anterior.

O usuário autorizou a publicação para validar com o agente real. A validação
manual no cliente real permanece pendente; o teste nativo de cursor não foi
reexecutado após a rejeição automática.

No Edge descartável foram observados worker antigo, recarga automática,
worker atualizado, reconexão e isolamento. A rodada completa do novo ensaio
não foi concluída antes da publicação solicitada pelo usuário.
