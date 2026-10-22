# Correção do conector e atualização integrada — 2026-10-22

- Objetivo: corrigir falha após atualização e sincronizar extensão com desktop.
- Baseline: `main`, HEAD `7fe9e8f`, árvore limpa, versão canônica `2.3.0`.
- Evidência do usuário: erro aponta para `common/logger.js:47`; mensagem causal ausente.
- Autorização: correções, testes, nova versão, commit/push/publicação e somente `main` ao concluir.
- Ambiente confirmado pelo usuário: VS Code; Maestri não conectado.
- Equipe: especificação, especialista extensão, especialista atualização, QA independente.
- Escopo: conexão/roteamento/abas, scripts de conteúdo e sincronização via instalador.
- Preservar: arquitetura, dados, perfis, credenciais, trabalho existente e distribuição legada.
- Segurança: concessão explícita de abas, isolamento entre agentes, SafetyGate fail-closed.
- Gate: `specification-planning` DONE antes de implementação delegada.
- Aceite: causa reproduzida e regressão coberta; aba escolhida funciona sem fallback ativo.
- Aceite: extensão canônica acompanha atualização do app; versões incompatíveis têm diagnóstico.
- Aceite: Python/Node/E2E descartável aprovados, revisão independente, build/instalador verificados.
- Aceite publicação: workflow verde, tag/release/instalador/checksum remotos conferidos.
- Aceite Git: somente `main`, removendo apenas ramos cujo conteúdo esteja preservado.
- Risco: migração de isolamento 2.3.0, múltiplos navegadores e extensão de pasta externa.
- Verificação: baseline separado; testes dirigidos; suíte integrada; Chromium temporário.
- Parar: regressão de segurança, perda de dados, credencial ausente para publicar ou bloqueio externo.
- Limite: teste descartável não comprova o cliente do usuário; relatar evidência separadamente.
- SPEC: aprovado `connector-update-spec.md`; diagnóstico reproduzido em teste Node.
- CONN-1: vínculo de concessões popup/sessão corrigido com fila e persistência temporária.
- UPD-1: identidade por navegador, recarga independente e diagnóstico de pasta externa.
- Revisão independente do handshake concluída sem falha bloqueante.
- Canal verificado: release `v2.3.0.45`, HEAD `7fe9e8f`, CI verde e dois assets.
- Próxima versão: `2.3.1` (CI acrescenta número da execução à release).
- Direção final do usuário: "lança a nova versão que eu faço o teste com meu agente".
- Aceite ajustado: publicar após os gates existentes de contrato/segurança/Node no CI;
  validação da recarga e do cliente real será feita pelo usuário na nova versão.
- E2E de recarga permanece diagnóstico manual; não bloqueia a release solicitada.
- Evidência local: Node 16 módulos PASS; E2E atual 5 cenários PASS; MCP congelado
  versão 2.3.1, 15 ferramentas, exit 0; instalador e checksum gerados/verificados.
- QA ampla local teve instabilidades de cursor/tempo; suíte completa será gate no CI.
- Status: preparando commit/push e release versionada, com validação do usuário pendente.
