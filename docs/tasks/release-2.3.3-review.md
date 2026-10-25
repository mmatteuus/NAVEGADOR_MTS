# Revisão técnica independente — 2.3.3

Data: 2026-10-25
Escopo: segurança e integração da alteração recuperada do stash `5ed9276b`.
Revisor: Codex independente; revisão somente leitura do código, testes e
documentação. Nenhuma janela, processo pessoal ou instalação foi usado.

## Resultado

**APROVADO no escopo revisado**, após a correção de identidade aplicada em
`src/mcp/router.py` e coberta por `tests/test_router_identity.py`.

O achado inicial era que, em `src/mcp/router.py`, `dispatch()` obtinha a identidade confiável de
`session_id`/`get_current_session_id()`. Porém, quando ambos estão ausentes,
o ramo `else` transforma `arguments["sessionId"]` em `trusted_sid`:

```python
else:
    trusted_sid = str(forged_sid).strip()
```

Assim, uma chamada sem identidade de transporte podia escolher a sessão de
outro agente nos próprios argumentos. Isso violava `multi-agent-reliability-brief.md`:
“nenhuma identidade fornecida em argumentos substitui a sessão”. Também deixa
incompleta a defesa descrita em `tests/test_adversarial_session_hijack.py`, que
cobre a ausência de sessão sem `sessionId`, mas não a ausência de transporte
com `sessionId` forjado.

Correção: aliases nos argumentos agora são aceitos somente quando coincidem
com a identidade do transporte/contexto; sem transporte são rejeitados, aliases
divergentes são rejeitados e `send_action`/executor não são chamados.

Reprodução independente executada para Computer Use: `computer_get_status` com
`sessionId` sem transporte retornou erro de forja e `computer_executor` teve zero
chamadas. Com `sessionId` e `session_id` divergentes, a chamada também retornou
erro antes do executor. A suíte `tests/test_router_identity.py` passou `5 passed`;
o lote integrado de hijack/HTTP/sem retry passou `12 passed`.

## Revisões aprovadas

- Pastas: `folder_paths`, `folder_handles`, `folder_assignments` e
  `folder_actions` validam raiz local, caminho relativo, escapes, reparse points,
  hardlinks, identidade de raiz, concessão por sessão, leases e versão de
  escrita. A suíte selecionada passou `38 passed, 1 skipped`.
- Janelas/entrada: atribuições registram HWND/PID/thread/geração; teclado e
  mouse revalidam identidade e revogação por sessão. A UIA usa `FOCUS_REQUIRED`
  para expansão de menus sem `allow_focus`; nenhum fallback físico foi criado.
- UIA: referências carregam HWND e geração da concessão; controles Win32 são
  limitados à janela atribuída e têm leitura posterior quando aplicável.
- WebSocket: respostas só resolvem requests no socket de origem; identidades de
  agentes não podem trocar de sessão na mesma conexão; abas novas não recebem
  concessão implícita.
- Atualização: `ws_update.js` usa a versão do manifesto, persiste estados,
  aguarda fila ociosa e limita recarga por versão; erros ficam explícitos.
- `stash@{2}` é histórico antigo da frente de teclado/abas. Suas melhorias
  relevantes já estão na ancestralidade atual (`72c962e` e descendentes), e não
  há delta funcional adicional a incluir além do stash recuperado. `stash@{1}`
  contém somente planos/specs de design já refletidos pelos commits de UI; deve
  permanecer preservado, sem ser aplicado como código.

## Gate para liberar

O bloqueio de identidade foi resolvido e revisado independentemente. O restante
do gate de release continua dependente da suíte integrada fresca, CI Windows e
verificação remota de tag, instalador e checksum. Menus UIA que exigem foco
continuam bloqueados por padrão, conforme a exigência de operar a janela já
aberta sem roubar foco.
