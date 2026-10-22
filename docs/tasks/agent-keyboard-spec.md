# Especificação: teclado virtual independente do agente

Status: SPEC DONE — implementação e validação local concluídas; ver agent-keyboard-validation.md.
Base: `f6719631033e6d0e3b972d2cf206d39ca73efd86`, worktree limpo na inspeção.

Implementado no builder: concessão popup-only em `storage.session`, seleção de
uma/muitas abas, validação central sem fallback ativo e screenshot fail-closed
para `tabId` explícito inválido ou aba não ativa no fallback.

## Objetivo e limites

Em `computer_keyboard_action` com `background` (padrão), o agente deve digitar
por canal virtual endereçado, sem `SendInput`, foco, cursor físico ou estado de
teclas do usuário. `background=false` continua sendo o caminho físico atual,
com a mesma autorização. Isolamento garantido é de dispositivo/foco; usuário e
agente no mesmo controle ainda podem intercalar texto e devem receber erro ou
aviso explícito quando isso for detectado.

O problema web é separado: `browser_*` deve operar numa aba concedida pelo
usuário e num alvo/caret virtual por documento, sem depender do foco do usuário.

## Evidência atual do baseline

- `keyboard_background.py` envia `WM_CHAR/WM_KEY*` por `PostMessageW`, mas
  resolve apenas `hwnd` explícito ou janela sob o cursor virtual.
- `mouse_background.py` possui cursor virtual thread-safe e `targetHwnd`.
- `computer/__init__.py` escolhe background por padrão; `computer_dispatch.py`
  preserva `background`/`hwnd`; `schemas_computer.py` os mantém opcionais.
- `SafetyGate` é default-deny, audita e revoga no kill-switch; `keyboard.py` é
  o caminho físico e deve permanecer inalterado em comportamento.
- A extensão hoje faz fallback para `getActiveTab()` quando `tabId` falta e
  `browser_type` depende do alvo/foco do content document.

## Contrato Computer Use

1. Background fixa `hwnd` explícito (ou o alvo virtual já fixado); captura
   identidade de PID/thread e revalida janela, identidade e foco antes de cada
   lote. Alvo inexistente/inválido falha fechado, sem janela ativa como fallback
   (`TARGET_INVALID`).
2. `type` usa fila serial do agente e retorna `background`, `targetHwnd`,
   `typedChars`; `press`/`hotkey` rejeita tecla/modificador desconhecido,
   envia keydown na ordem e keyup reverso.
3. `SafetyGate` é verificado na chamada e antes de cada lote; lock serial evita
   interleaving entre chamadas, e revogação ou kill-switch cancela trabalho
   subsequente e libera modificadores. Falha de `PostMessageW`
   aborta e limpa. Não usar `SetForegroundWindow`, `SetFocus` ou `SendInput`.
4. Físico continua em `type_text`/`press_key`; schemas, nomes e defaults legados
   permanecem compatíveis e nenhum campo novo vira obrigatório.
5. Controle que exige foco, raw input, DirectInput, UWP restrita ou mensagens
   customizadas pode rejeitar a entrega (`TARGET_INVALID`/`TARGET_IN_USE`);
   não há fallback para foco físico, CDP ou clipboard. `PostMessageW` não é uma
   segunda pilha física e não promete entrega universal a qualquer HWND.

## Contrato Browser Use e seleção de abas

O popup confiável oferece checkboxes para uma ou várias abas, `Salvar` e
`Limpar`. A concessão fica em `chrome.storage.session` (não `storage.local`):
IDs sobrevivem reinício do service worker, mas são apagados no reinício total
do navegador para evitar reutilização de ID. O popup é o único concedente.
O popup também oferece URL `http/https` e “Abrir e liberar”: cria a aba
inativa e concede-a atomicamente; URLs `chrome:`, `data:`, `file:` e scripts
são rejeitadas. Isso permite liberar abas pessoais já abertas ou recém-criadas;
`browser_new_tab` do agente nunca concede a própria aba.

Toda ação de página (`navigate`, snapshot, screenshot, evaluate, click, type,
scroll, hover, press) valida `tabId` concedido. Sem `tabId`, só aceita quando
existe exatamente uma aba concedida; caso contrário retorna
`TAB_SELECTION_REQUIRED`. ID ausente, fechado ou não concedido retorna
`TAB_NOT_ALLOWED`; nunca usa a aba ativa silenciosamente.

`list` pode listar metadados para o popup. `new` é inativa por padrão e nunca
concede a nova aba automaticamente. `switch` e `close` só atuam em aba
concedida; foco/janela exige pedido explícito. `close` revoga após sucesso.
Navegar conserva a concessão do `tabId` (a UI explica que é a aba inteira, não
uma trava de URL). Fechamento, desconexão ou ID reutilizado exigem nova seleção.

## Teclado web por documento

Cada documento/aba concedido mantém alvo e caret virtuais fora de
`document.activeElement` e `window.getSelection()`. `click`/`type` pode receber
`selector`, `ref` ou coordenadas; um clique apenas registra o alvo/caret virtual
e nunca chama `focus()`. Sem esses dados, usa somente o último alvo do agente na
mesma aba/documento; nunca o activeElement. Se o alvo coincidir com o editable
ativo do usuário, retorna `TARGET_IN_USE` sem escrever.

Suportar `input`, `textarea` e `contenteditable` simples. `type` deve preservar
setter/eventos compatíveis com React/Vue, `clearFirst` e `submit`; `press` e
atalhos operam no alvo virtual. Atalhos que exigem foco, clipboard, selection
real ou APIs não suportadas falham fechado, sem CDP/foco físico alternativo.

## Grafo de implementação e revisão

**KBD-1:** implementar estado de alvo/caret, fila, resolução segura e limpeza em
submódulos <150 LOC; conservar funções públicas background.

**KBD-2 (após KBD-1):** ajustar dispatcher/schema somente se necessário; manter
caminho físico e contratos.

**TAB-1:** implementar popup, concessão session, Save/Clear e estados fechado/
reutilizado; **TAB-2 (após TAB-1):** impor allowlist em todas as ações e
lifecycle sem fallback ativo.

**WEB-1 (após TAB-1):** implementar alvo/caret por documento, eventos/setter e
erros fail-closed para activeElement, clipboard e atalhos não suportados.

**QA (após KBD-2/TAB-2/WEB-1):** testes unitários/mocks de ordem, Unicode,
concorrência, revogação, allowlist uma/muitas abas, reinício SW/browser,
fechamento/reuso, React, contenteditable e regressões. Validar cliente Chrome
real separadamente dos mocks, com SHA, ambiente e dirty state.

## Aceitação e riscos

- Usuário digita em outra janela/aba enquanto o agente atua: foco, cursor e
  input do usuário permanecem intactos; nenhuma API física é chamada.
- Sem SafetyGate/toggle, toda ação rejeita com `isSecurityBlock`; kill-switch
  deixa zero lotes/modificadores pendentes.
- Ação web fora da concessão ou sem seleção inequívoca nunca chega ao Chrome.
- Usuário consegue abrir e liberar URL HTTP(S) pelo popup; a aba nasce inativa
  e pode ser usada por `tabId` explícito ou implicitamente quando for única.
- Mesmo controle compartilhado, alvo inválido, documento incompatível, foco
  necessário ou shortcut não suportado retornam erro estável sem fallback.
- Não alterar `BROWSER-MCP-MTS-PORTATIL/`; testes existentes devem permanecer
  verdes e a contagem/LOC deve ser verificada.
