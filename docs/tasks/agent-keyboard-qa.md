# Relatório QA independente — teclado e abas do agente

Data: 2026-10-22 (America/Sao_Paulo)

## Identidade

- SHA inicial/base: `f6719631033e6d0e3b972d2cf206d39ca73efd86`.
- Branch final auditada: `feat/teclado-isolado-guias`.
- Estado: dirty por alterações da implementação e testes dos builders; nenhum
  reset, clean, commit ou processo externo foi executado pelo QA.
- Fingerprint SHA-256 final independente calculado no checkout compartilhado do
  conjunto ordenado de 88 arquivos regulares sob
  `src/`, excluindo `__pycache__`:
  `3381db6a0246bc8e22911ea347774598ef64572f81ec743666a4d2c4e88ba2c5`.
  Cada entrada é `caminho relativo SHA-256`, ordenada lexicograficamente e
  terminada por newline UTF-8. O manifesto está em
  `temp/keyboard-source-fingerprint-qa.txt`. A diferença anterior veio da
  ordenação: `sorted(Path)` deve ser usada diretamente, conforme a expressão
  canônica, sem `key=p.as_posix`. A ordenação ordinal alternativa produziu
  `17109d69afd4c7f921e1b6c6a2561e7e00e87c7dce13aab50c6125028fa2f6d5`; os 88
  hashes individuais são iguais, portanto a revisão de fingerprint está
  **PASS / BOUND** pelo valor canônico Windows Path.

## Testes executados

- `node tests/test_*.mjs`, sequencialmente, excluindo o E2E opt-in real:
  **13 PASS, 0 FAIL**.
- `node tests/test_keyboard_browser_e2e.mjs` foi separado como E2E opt-in e
  bloqueou neste ambiente por módulo `playwright` ausente; não foi tratado como
  falha de mock ou do produto.
- Na rodada inicial independente, `pytest` teve **218 PASS, 1 FAIL**; a rodada
  final do root registrou **219 PASS, 3 FAIL**. As falhas adicionais foram
  verificações de cursor físico em ambiente onde o mouse do usuário se moveu;
  o código de mouse não fazia parte desta mudança.
- `tests/test_agent_keyboard_contract.py` e
  `tests/test_keyboard_background_isolation.py`: **12 PASS**.
- `node tests/test_agent_tab_policy.mjs`: **PASS**.
- `C:\Python314\python.exe tests/keyboard_native_probe.py`: **PASS**; texto,
  foco, cursor e controle não alvo preservados.
- E2E real Chromium executado pelo root: **PASS** em
  `temp/keyboard-e2e-FXRtnY-G`; cobriu Save/Clear do popup, nova URL inativa
  concedida, digitação concorrente, Enter, Ctrl+A, exclusão e reinício do
  navegador limpando concessões.
- Verificação de modularidade: **0 arquivos acima de 150 LOC** em `src/` e
  `tests/`.

## Falha conhecida

`tests/test_adversarial_cursor_and_safety.py::test_prod_pids_untouched` falha
porque o PID legado `17892` não existe neste ambiente. A mesma asserção consta
em `git show f671963:tests/test_adversarial_cursor_and_safety.py`; a falha é
pré-existente e não indica encerramento causado pelo QA.

Foram excluídos da suíte geral `test_computer_automation.py` e
`test_challenger_tier5_win32.py`, pois executam entrada física autorizada na
área de trabalho do usuário. O probe nativo separado valida somente a janela
de teste e não interage com o cursor/foco do usuário.

## Revisão de contrato

- Concessões ficam em `chrome.storage.session`, só o popup confiável pode
  conceder/remover, e fechamento ou reutilização de ID revoga a concessão.
- Alvo único implícito é permitido; zero ou várias abas exigem `tabId`.
- Abertura pelo popup usa URL HTTP(S), `active: false` e concessão explícita.
- Dispatcher valida concessão antes de navegação, snapshot, screenshot,
  avaliação, interação, rolagem e teclas; não há fallback silencioso para aba
  ativa.
- Teclado Windows background usa `PostMessageW`, fixa identidade do HWND,
  revalida antes dos lotes e libera modificadores em falha.
- Teclado web usa alvo virtual sem `focus()`/clipboard/`document.activeElement`
  como fallback e recusa o campo que está sendo usado pelo usuário.

Validação em navegador Chrome real permanece separada do mock; o QA local não
declara essa evidência sem o E2E real correspondente.
