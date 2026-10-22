# Especificação de release: teclado isolado e seleção de abas

Status: SPEC DONE — pronta para execução pelo responsável de release.
Data de inspeção: 22/10/2026. Checkout: `feat/teclado-isolado-guias`, HEAD
`f6719631033e6d0e3b972d2cf206d39ca73efd86`, worktree já contém mudanças locais.
Remote `main` aponta exatamente para esse SHA; não há release pública confirmada.

## Decisão de versão

Na inspeção inicial, `src/version.py` e `src/extension/manifest.json` estavam em
`2.2.0`, então versão canônica dos testes e updater. O próximo release deve
usar base `2.2.1`. O workflow gera a versão publicável `2.2.1.<GITHUB_RUN_NUMBER>` em
checkout efêmero com `prepare_release.py`; não escolher nem inventar o número
antes da execução. Não alterar manualmente `src/version.py`, manifest ou
`installer.iss` para um quarto componente, pois isso quebraria o formato de
desenvolvimento; o Builder deve atualizar os três para `2.2.1`.

## Cadeia confirmada

`.github/workflows/windows-qa.yml` roda sintaxe/extensão em Ubuntu, contratos
Python e extensão em Windows, e compilação do instalador após contratos. O job
`release` só roda em `push` para `main` ou `workflow_dispatch` em `main`, com
permissão `contents: write` e concorrência `release-main` sem cancelamento.

No job release, `prepare_release.py` valida base/run/commit, estampa versão
quádrupla somente no checkout CI e produz `release-metadata.json`. Depois,
`build_exe.py` gera PyInstaller e copia a extensão; `build_installer.py` usa
Inno Setup e exige manifest empacotado e versão congelada coerente.

O instalador canônico é `dist_installer/NAVEGADOR_MTS_Instalador_v2.2.1.N.exe`.
O job cria `NAVEGADOR_MTS_Instalador_v2.2.1.N.sha256`; `publish_release.py`
valida SHA local, HEAD igual ao commit dos metadados, tag `v2.2.1.N`, ordem
semântica, e confirma via API que ambos assets e digest remoto existem.

## Grafo mínimo de execução

1. Root revisa diffs da feature, preserva mudanças não relacionadas e confirma
   que nenhum segredo, build local ou distribuição legada será incluído.
2. Rodar suíte Python, testes JS relevantes, checagem de LOC e inspeção do
   instalador antes de qualquer publicação. Registrar SHA, estado dirty limpo,
   comandos e resultados.
3. Builder atualiza `src/version.py`, `src/extension/manifest.json`,
   `installer.iss` e testes de versão para `2.2.1`; atualiza o envelope de
   protocolo que hoje contém `2.1.1` para usar `runtime.getManifest().version`,
   preservando o envelope MCP. O Builder também troca o PID fixo do teste
   sentinel por snapshot dos processos protegidos vivos no início da sessão;
   o sentinel autouse de `conftest.py` permanece.
4. Criar commit único/reversível da preparação e feature. Entregar por
   fast-forward-only da branch para `origin/main`/`main`, sem merge commit,
   force push ou reset; HEAD remoto inicial confirmado é `f671963...`.
5. Disparar o workflow por push ou `workflow_dispatch` em `main`. Não editar
   artefatos CI localmente para simular publicação.
6. Após sucesso, verificar remotamente HEAD de `main`, execução concluída, tag
   `v2.2.1.N`, release não draft e assets `.exe`/`.sha256` com digest igual ao
   local reportado pelo CI. Só então informar URL/tag/asset como publicado.

## Critérios de aceitação

- Workflow `sintaxe`, `contratos` e `instalador` passam no mesmo commit do
  release; testes locais não substituem os jobs Windows.
- Metadata aponta para SHA completo do commit publicado e a tag aponta para o
  mesmo SHA; não há release fora de ordem ou tag reaproveitada.
- Asset é instalador full versionado, não ZIP/source; checksum acompanha o
  executável e o digest remoto é verificado pelo script.
- Manifest empacotado e executável congelado reportam a versão CI quádrupla;
  fonte canônica e fallback local reportam `2.2.1`.
- A atualização só é considerada disponível após evidência remota do asset;
  falha/timeout/404 permanece `BLOCKED`, sem alegar publicação.

## Riscos e stop conditions

Parar antes do push se houver diff não compreendido, branch divergente, falha
de testes, segredo detectado, runner/credencial GitHub indisponível ou workflow
sem evidência do asset. A falha histórica do workflow 40 não substitui a
execução atual nem bloqueia o push por si só; a execução atual deve passar.
Não instalar, substituir produção, iniciar processos legados ou modificar
`BROWSER-MCP-MTS-PORTATIL/` como parte desta release.

## Evidência local da preparação

- Fontes, manifesto e fallback Inno atualizados para `2.2.1`.
- Handshake lê a versão efetiva do manifesto; suíte de updater cobre migração
  de `2.2.0.41` para `2.2.1` e novas versões com quatro componentes.
- 55 testes Python de teclado, contrato, versão, updater, publicação e sentinela
  passaram. O teste de artefatos foi desmarcado apenas localmente porque `dist/`
  ainda contém a compilação anterior; esse diretório ignorado não entra no push.
- 14 módulos de testes Node passaram; E2E real de Chromium/extensão/bridge MCP
  passou com perfil temporário em `temp/keyboard-e2e-6gQ0mb`.
- Revisão independente conferiu versão, guard de processos, protocolo e LOC.
- Validação do instalador publicado depende da execução remota após o push.
