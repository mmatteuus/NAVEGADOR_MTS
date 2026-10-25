# QA E2E da release 2.3.3 — 2026-10-25

## Escopo

Execução independente em Chromium descartável, com perfis temporários, páginas
HTTP locais, bridge MCP temporária e extensão copiada para `temp/e2e-real`.
Nenhuma aba, janela, perfil ou programa do usuário foi acessado.

## Ambiente

- Chromium Playwright: `chromium-1243/chrome-win64/chrome.exe`.
- Módulo Playwright local do runtime Codex.
- Testes serializados; nenhuma ação física de mouse/teclado.
- Perfis e processos encerrados pelos próprios fixtures após cada caso.

## Comandos e resultados

```text
$env:RUN_EXPLICIT_ASSIGNMENT_E2E='1'; node tests/e2e_real/test_explicit_agent_assignment.mjs
PASS: atribuição concorrente, bloqueio cruzado, reassociação, revogação e foco preservado.
exit 0

$env:QA_RUN_REAL_E2E='1'; node tests/e2e_real/test_connector_popup_update.mjs
PASS: popup grant, tabId explícito/implícito, isolamento, revogação e reload.
exit 0

$env:RUN_PWA_AGENT_E2E='1'; node tests/e2e_real/test_pwa_agent_isolation.mjs
PASS: PWA real offline, SW/cache, atribuição cruzada negada e foco/campos preservados.
exit 0
```

## Evidência

O primeiro caso comprovou duas atribuições simultâneas, bloqueio cruzado,
reatribuição, revogação e preservação de foco/campos. O segundo comprovou que
um worker antigo `2.2.0` recarrega como atualização e mantém as concessões por
agente. O terceiro comprovou Service Worker/cache offline do PWA, isolamento e
preservação do foco após digitação concorrente.

## Limites

Esses testes não provam instalação no cliente pessoal, atualização do navegador
real do usuário, menus do VS Code ou controle de programas reais. A política de
foco continua `FOCUS_REQUIRED` para menus; isso preserva a exigência da janela
existente sem consentimento implícito para roubar foco.

## Veredito

PASS para os três fluxos E2E descartáveis. A revisão de código, suíte Python,
build Windows, CI e digest remoto permanecem gates separados da publicação.
