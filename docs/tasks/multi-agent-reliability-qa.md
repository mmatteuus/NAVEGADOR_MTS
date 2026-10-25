# Evidências locais — confiabilidade e destinos por agente

Data: 2026-10-25. Branch: `work/isolamento-agentes-20261025`.
Base: `9cfceb7`. Alterações não publicadas; objetivo completo permanece ativo.

## Evidência repetida pelo coordenador

- E2E real de atribuição explícita: PASS, exit 0. Duas sessões HTTP inicializadas,
  extensão real, bridge e perfil temporários, digitação concorrente, bloqueio
  cruzado, reatribuição e revogação. Campos, seleção, activeElement e estado active
  das guias permaneceram iguais. Comando:
  `$env:RUN_EXPLICIT_ASSIGNMENT_E2E='1'; node tests/e2e_real/test_explicit_agent_assignment.mjs`.
- E2E real de atualização: PASS, exit 0. Worker antigo 2.2.0 encerrou; novo worker
  carregou 2.3.2 com motivo update. Popup concedeu guia explicitamente ao agente A;
  agente B e acesso após revogação foram negados. Comando:
  `$env:QA_RUN_REAL_E2E='1'; node tests/e2e_real/test_connector_popup_update.mjs`.
- Causa da falha inicial de reload: perfil descartável sem Developer Mode.
  developerPrivate informou DISABLED/unsupportedDeveloperExtension, sem erro no
  manifesto. Habilitar Developer Mode somente nesse perfil fez o caso mínimo e
  o E2E completo passarem. Nenhum perfil pessoal foi alterado.
- Suite Node integrada: 20 módulos PASS. Inclui recuperação de leitura do storage
  após erro, persistência de atribuições e bloqueio de popup com proprietário
  desatualizado. O teste adicional de reinjeção de content bridge passou.
- Atualização revalidada por revisão independente final: a versão vem do manifesto
  local; flags contraditórias não confirmam versão antiga; falha na segunda gravação
  não recarrega; requestedAt impede novo ciclo após erro/reconexão da mesma versão.
- Python UI/entrada/contratos: 40 PASS. Inclui construção real da UI fora da área
  visível, largura mínima, seleção readonly, UIA, HWND reutilizado e roteamento.
- Python arquivos/transporte: 24 PASS, 1 SKIP. Junction real bloqueada; symlink
  comum indisponível no runner. Handles reais impedem escrita/rename concorrente,
  versões antigas não sobrescrevem e concessões não atravessam sessões.
- Fixture Windows `python tests/uia_native_probe.py`: PASS, exit 0. HWNDs próprios
  com message pump na thread criadora; execução via execute_mcp_computer e worker
  real. EDIT teve leitura de confirmação, captura limitada, revogação negada;
  BUTTON foi invocado e BM_GETCHECK confirmou mudança. Foreground e cursor iguais
  antes/depois, inclusive após o botão.
- Probe PyInstaller `temp/package-qa/dist2/uiacompat2.exe`: executado pelo
  coordenador, exit 0, UIA_IMPORT_OK uia. Prova de import/COM empacotado; não equivale
  a instalador completo nem homologação da aplicação pessoal.
- compileall de src e git diff --check passaram. Limite físico de 150 linhas
  passou no lote de UI/contratos. Lotes se sobrepõem; não somar suas contagens.

## Revisão independente

Quatro especialistas Codex foram usados e reaproveitados. Registro com comando
Python amplo e exclusões em [QA independente](multi-agent-independent-qa.md):
76 PASS, 1 SKIP no snapshot revisado. Revisão encontrou e corrigiu:
respostas ligadas a socket errado; retry sem sessão; criação de guia concedendo
acesso implicitamente; lease trocado durante digitação; persistência de donos
com falha; refs UIA reutilizáveis; retorno de escrita sem comprovação.
Revisão posterior da UIA: 6 PASS para snapshots, falha sem replay, readback,
revogação durante resolução, limitação de árvore e captura de HWND alheio.
Lote final de política/UIA/UI/limite de linhas/guard de build: 19 PASS. Menus que
exigem ExpandCollapse são recusados com FOCUS_REQUIRED por padrão. Campos do
agente não habilitam foco; essa permissão pertence à concessão humana da janela.

## Estado funcional e limites

O painel Destinos reúne Programas e Pastas e arquivos. A atribuição exige agente
ativo selecionado; janelas têm identidade HWND/PID/thread e concessão por geração.
Pastas têm raiz exclusiva, paths relativos, versão de arquivo, limites de tamanho
e bloqueio de reparse/hardlinks. A escrita no handle não promete atomicidade
contra queda de energia nem modifica buffers ainda não salvos do VS Code.

A UIA do VS Code com acessibilidade ativa expôs menus e acionou Help em perfil
descartável. O próprio menu Electron mudou o foreground: isso NÃO atende a
independência total de foco no desktop compartilhado. Esse caminho agora fica
bloqueado por padrão, aguardando a política humana de foco. O usuário exige exatamente
a janela já aberta; outra instância/ambiente foi descartada. Está pendente escolher
entre liberação humana do foco, funções equivalentes sem abrir menu ou permissão
de foco temporário. Não presumir essa permissão.

Os testes de navegador usam páginas locais, não todos os PWAs instalados ou o
chat final. Nenhum programa pessoal foi atribuído/operado, nenhum instalador novo
foi aplicado e não houve commit, push, publicação ou release. Ambiente .venv
documentado não existe; Python 3.14 instalado foi usado, com dependências UIA
somente em temp/qa-python. Nenhuma instalação Python global foi modificada.
