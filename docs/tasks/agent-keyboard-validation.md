# Validação final local — teclado e guias

Data: 2026-10-22. Branch `feat/teclado-isolado-guias`, base
`f6719631033e6d0e3b972d2cf206d39ca73efd86`, alterações sem commit.
Equipe: coordenador e quatro subagentes independentes para especificação/UI,
teclado web, teclado Windows e QA/revisão.

## Resultado final

Implementação validada localmente: alvo/caret virtual, seleção de uma ou várias
guias pessoais existentes, abertura e liberação de URL pelo popup, bloqueio de
guias não permitidas, teclado background Windows e preservação do modo físico
explícito. O usuário deve ativar a extensão atualizada conforme o
[guia de uso](../TECLADO_E_GUIAS_DO_AGENTE.md).

Fingerprint SHA-256 dos 88 arquivos regulares em `src/`, excluindo
`__pycache__`: `3381db6a0246bc8e22911ea347774598ef64572f81ec743666a4d2c4e88ba2c5`.
Algoritmo: ordenar caminhos relativos por `Path` no Windows (sem distinguir
maiúsculas); para cada arquivo gerar uma linha
`caminho SHA-256`; calcular SHA-256 do conjunto UTF-8 terminado em newline.
Manifesto local: `temp/keyboard-source-fingerprint.txt`.
O QA usou ordem ordinal de strings, obtendo
`17109d69afd4c7f921e1b6c6a2561e7e00e87c7dce13aab50c6125028fa2f6d5`.
Os 88 arquivos são idênticos; ambos os hashes foram reproduzidos no mesmo
comando para comprovar que a diferença é apenas a ordem das entradas.

## Evidência terminal do coordenador

1. `python -m pytest -q -p no:cacheprovider
   tests/test_keyboard_background_isolation.py
   tests/test_keyboard_background_keys.py tests/test_agent_keyboard_contract.py
   tests/test_mcp_computer_adapter.py tests/test_adversarial_m4_schemas.py`:
   **24 passed in 0.35s**, exit 0.
2. Cada `tests/test_*.mjs`, excluindo o E2E opt-in, executado sequencialmente:
   **13 PASS, 0 FAIL**, exit 0.
3. `python tests/keyboard_native_probe.py`: **PASS**, exit 0. Controles EDIT
   próprios receberam Unicode; outro controle, foco e cursor foram preservados.
4. `node tests/test_keyboard_browser_e2e.mjs`: **PASS**, exit 0, usando
   Playwright 1.63.0 e Chromium 1243 em perfil descartável headless. Extensão
   real e roteador MCP/WebSocket reais, páginas loopback e portas dinâmicas.
5. `git diff --check`: exit 0. Nenhum arquivo de código/teste acima de 150 linhas.

O E2E final comprovou: digitação concorrente em campos distintos na mesma guia;
foco do usuário preservado; recusa do campo em uso; caret e emoji no meio do
texto; cancelamento de beforeinput; Ctrl+A e exclusão; Enter em textarea;
submissão; Save/Clear preservando os checkboxes; abrir e liberar nova guia
inativa; seleção múltipla exigindo tabId; retirada de acesso; navegação mantendo
a concessão; reinício completo do navegador limpando concessões.

Artefatos da rodada final: `temp/keyboard-e2e-FXRtnY/`, incluindo
`popup-guias.png`, inspecionado visualmente. Só a cópia descartável da extensão
teve a porta WebSocket substituída pela porta dinâmica do teste.

## Limites da regressão ampla

Comando: `python -m pytest tests -q -p no:cacheprovider
--basetemp=temp/qa-root-final-1022 --ignore=tests/test_computer_automation.py
--ignore=tests/test_challenger_tier5_win32.py`.

Resultado final: **219 passed, 3 failed in 31.72s**. Não é um PASS global:

- `test_prod_pids_untouched` exige PID legado 17892, ausente antes do trabalho;
  a mesma asserção está na base Git.
- `test_background_mouse_does_not_alter_physical_cursor` e
  `test_background_scroll_and_drag` observaram posições diferentes enquanto o
  cursor do desktop se movia. A rodada independente anterior passou nesses
  testes. Os módulos de mouse não foram alterados; esta observação não prova
  regressão do teclado nem comprova ausência universal de interferência.
- Dois módulos de testes físicos foram excluídos para evitar teclado/mouse
  físicos na área de trabalho do usuário. O probe nativo usa controles próprios.

O [relatório independente](agent-keyboard-qa.md) registra revisão e fases de QA.
O E2E valida páginas locais controladas, não todos os sites ou editores ricos.
O canal Windows confirma enfileiramento, não aceitação por qualquer aplicativo.
Nenhum instalador foi gerado/aplicado; publicação, commit e push não ocorreram.
