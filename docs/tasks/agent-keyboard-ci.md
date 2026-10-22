# Especificação: diagnóstico público do CI Windows

Status: SPEC DONE — pronta para implementação.
Contexto observado: commit `475200b` foi enviado para `main`; execução 41
falhou no job Windows e o release foi pulado. Logs autenticados não estão
disponíveis neste ambiente; nenhuma credencial deve ser extraída ou reutilizada.

## Objetivo

Quando o job Windows falhar, a execução deve publicar no log público o nome de
cada teste Python falho e uma mensagem curta derivada do JUnit XML. O diagnóstico
deve tornar a próxima correção possível sem esconder o status real do job.

## Implementação mínima

1. Criar `report_test_failures.py` na raiz, somente com biblioteca padrão:
   aceitar caminho JUnit XML, parsear `testsuite`/`testsuites`, localizar
   `failure`/`error`, extrair `classname`, `name` e texto, limitar a mensagem a
   tamanho fixo seguro e emitir linhas GitHub Actions `::error title=...::...`.
2. O script deve tratar XML ausente/malformado com erro não zero e mensagem
   clara; não expor ambiente, tokens, caminhos sensíveis ou conteúdo ilimitado.
3. Adicionar teste focado em `tests/test_report_test_failures.py` cobrindo XML
   com falha e erro, truncamento/escape de annotation e XML inválido/ausente.
   O teste não depende de rede, runner Windows ou processos de produção.
4. No job `contratos` de `.github/workflows/windows-qa.yml`, trocar o comando
   pytest para `python -m pytest -q --junitxml=test-results.xml`.
5. Após os testes, adicionar step com `if: ${{ always() }}` que executa o
   reporter contra o arquivo. Se o arquivo não existir, o step deve produzir
   diagnóstico e falhar; não usar `continue-on-error`.
6. Adicionar upload do XML como artifact de retenção curta em step `always()`
   somente para diagnóstico, mantendo o status do job determinado pelo pytest.
   O artifact não pode conter segredos nem substituir o gate de testes.

## Invariantes e limites

- Não adicionar `continue-on-error`, skips, xfails, filtros de teste ou alteração
  de `needs`/condições do release.
- O job `release` continua dependendo de `sintaxe` e `contratos`; diagnóstico
  não transforma falha em sucesso.
- Manter limites de modularidade: script e teste abaixo de 150 linhas; workflow
  deve continuar legível e sem comandos destrutivos.
- Não consultar GitHub API, credenciais, secrets, banco, processos de produção
  ou arquivos fora do workspace.
- O reporter deve escapar `%`, `\r`, `\n` e caracteres que quebrem a sintaxe
  de command annotation; a mensagem é informativa, não um shell script.

## Critérios de aceitação

- Falha simulada em XML produz annotation com `classname::name` e mensagem
  limitada; erro simulado também é reportado.
- XML válido sem falhas não produz erro do reporter.
- XML ausente ou inválido retorna exit code não zero e texto objetivo.
- O workflow preserva o exit code do pytest, publica `test-results.xml` quando
  possível e mostra nome/mensagem da falha no log público.
- Execução verde continua passando todos os gates e libera o release somente
  quando `sintaxe`, `contratos` e demais dependências passam.
- Uma nova execução do CI fornece evidência suficiente para identificar o
  primeiro teste Windows falho sem acesso privilegiado aos logs.

## Grafo e stop conditions

Builder implementa o script/teste; workflow builder integra os steps; QA roda o
teste focado e valida YAML/sintaxe. Parar se o parser exigir dependência nova,
se a annotation puder vazar segredo, se o step mascarar exit code ou se o
artifact alterar gates. Depois, abrir nova execução CI; não declarar release
até o job Windows passar.
