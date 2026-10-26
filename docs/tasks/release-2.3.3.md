# Publicação 2.3.3 — 2026-10-25

## Objetivo e autorização

Integrar todas as melhorias existentes à main e publicar nova versão para o
canal de atualização das instalações existentes, conforme solicitação explícita
do usuário nesta sessão. Commit, integração e push/publicação estão autorizados.
A instalação na máquina pessoal permanece separada da publicação.

## Baseline e recuperação

- Main local/remota: 6760f6a; branch de trabalho: 9cfceb7.
- Dois commits de acessibilidade do popup estão acima da main.
- Stash 5ed9276b preserva 107 arquivos da frente de isolamento por agente.
- Recuperado com stash apply, sem excluir o stash e sem conflitos.
- Stashes anteriores permanecem preservados; revisar cobertura antes de concluir.
- Última release pública consultada: v2.3.1.73, commit 72c962e.
- Especificação funcional: multi-agent-reliability-brief.md (SPEC DONE).
- Menus que exigem foco continuam bloqueados; não inferir consentimento de foco.

## Especificação de release — SPEC DONE

REL-SPEC: arquiteto independente revisou versão, instalador, updater e workflow.
Versão base: 2.3.3, igual em src/version.py, manifesto e fallback do instalador.
O workflow acrescenta seu número de execução somente no checkout de compilação.
Preservar AppId, diretório e consentimento do atualizador; distribuir instalador
completo e checksum. Não alterar legado, perfis, dados ou credenciais.

## Grafo de execução e gates

1. REC: recuperar stash e conferir arquivos/escopo — concluído.
2. BUILD: sincronizar versão, regressões e formatação — após SPEC DONE.
3. QA: revisão independente do código e testes locais seguros.
4. GIT: commit restrito e integração à main, preservando histórico e stashes.
5. CI: push autorizado, acompanhar testes completos em Windows descartável.
6. RELEASE: conferir SHA, tag, release latest, instalador PE e SHA-256.
7. UPDATE: verificar detecção por versões anteriores usando o canal real.

## Critérios de aceite e evidência

- Melhorias recuperadas e commits de acessibilidade presentes na main.
- Testes Node, sintaxe e Python selecionados aprovados em ambiente local.
- Testes que interagem com desktop real ficam no runner descartável do CI.
- Não coletar pytest fora de tests: temp contém dependências e fixtures antigas.
- Revisão independente sem defeitos bloqueantes no escopo da publicação.
- CI completo e release aprovados para o SHA publicado.
- Instalador e checksum baixados conferem com digest publicado no GitHub.
- Atualizador classifica a nova release como mais recente para versões antigas.
- Disponibilidade no canal não equivale à instalação em todos os clientes.

## Riscos e condições de parada

Parar publicação em regressão de segurança, testes bloqueantes, perda de trabalho,
divergência remota ou inconsistência de versão/asset/digest. Não executar ações
físicas nem instalar no cliente pessoal para validar. Acesso remoto pelo Git e
API pública: gh não possui login disponível; workflow usa credencial própria.

## Execução

Versão sincronizada em 2.3.3. Recuperação e revisão do escopo concluídas:
stash antigo de código já está representado no histórico; stash de design tem
somente planos. Todos permanecem preservados.

QA independente: Python seguro 76 PASS/1 SKIP e lote adicional 33 PASS;
Node 23 módulos PASS e reinjeção de content bridge PASS. E2E real descartável:
atribuição explícita, atualização da extensão e PWA offline PASS.
Revisão independente encontrou e confirmou a correção de identidade descrita
abaixo. Coordenador repetiu contratos de identidade/HTTP/WS/recarga/release:
27 PASS. As contagens de lotes se sobrepõem e não devem ser somadas.

Relatórios: release-2.3.3-qa.md, release-2.3.3-e2e.md e
release-2.3.3-review.md. Compilação local interrompida no COLLECT do PyInstaller
com OSError errno 12 ao copiar tzdata; espaço livre verificado: C > 78 GB,
D > 1 TB. Não classificar como disco cheio. O executável havia sido gerado,
mas o pacote/instalador local não está validado. O CI Windows limpo fará a
compilação completa, obrigatória antes da publicação automática.
Verificação remota permanece pendente até a execução para o SHA final.

## Correção do gate CI 77 — SPEC DONE

O CI 40221544162 bloqueou publicação: mock de bridge sem session_id, testes de
cursor anteriores à concessão obrigatória de janela e ws_client.js com 150 linhas
onde a suíte exige menos de 150. Adaptar fixtures ao contrato aprovado, mantendo
as assertivas de concorrência e concessões reais do registro com Win32 simulado.
Não remover testes, enfraquecer isolamento nem acionar janelas do usuário.
Reduzir apenas espaço vertical de ws_client.js; executar testes afetados e
revisão independente antes de novo push. O instalador não foi publicado no CI 77.

## Addendum SPEC DONE — identidade confiável no router

Antes da publicação, `MCPToolRouter.dispatch` deve aceitar a identidade somente
do parâmetro confiável `session_id` ou do contexto de transporte. Os aliases
`sessionId` e `session_id` dentro dos argumentos são apenas validações: qualquer
alias sem identidade confiável deve ser rejeitado antes de chamar bridge ou
executor; com identidade confiável, ambos devem coincidir entre si e com ela.
Chamadas sem aliases e sem identidade preservam a compatibilidade anônima.
Aceite: teste dedicado comprova rejeição dos dois aliases e de divergências,
aceita contexto/parâmetro confiável e demonstra zero chamadas ao executor.
