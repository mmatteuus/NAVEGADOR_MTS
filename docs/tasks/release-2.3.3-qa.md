# QA independente da publicação 2.3.3

Data: 2026-10-25

Escopo: validar código recuperado do stash e os contratos da release sem tocar
foco, cursor, teclado, mouse, programas ou instalação pessoal do usuário.

## Evidências executadas

| Gate | Comando | Resultado |
| --- | --- | --- |
| Sintaxe Python | `python -m compileall -q src entrypoint.py stdio_entrypoint.py` | PASS (exit 0) |
| Extensão MV3 | `node tests/run_extension_suite.mjs` | PASS (23 testes reportados) |
| Reload do content bridge | `node tests/test_content_bridge_reload.mjs` | PASS |
| Contratos MCP/WS/sessões/storage/pastas | seleção explícita de 21 módulos pytest | PASS: 76, 1 skip, 5,13 s |
| Atribuições/UIA simulada | seleção explícita de 11 módulos pytest | PASS: 33, 3,63 s |
| Integridade do diff | `git diff --check` | PASS |

O teste de pastas teve um skip porque symlink comum não está disponível neste
ambiente. Os testes de UIA e input usaram mocks; não houve chamada de foco ou
entrada física. Os probes nativos e de VS Code ficaram fora deste gate.

## Comandos reproduzíveis

```text
python -m pytest -q tests/test_mcp_protocol.py tests/test_mcp_http.py tests/test_mcp_ws_bridge.py tests/test_mcp_ws_multisession.py tests/test_multisession_concurrency.py tests/test_ws_extension_routing.py tests/test_ws_response_ownership.py tests/test_agent_directory.py tests/test_agent_actions_ws.py tests/test_m1_refactoring_and_schemas.py tests/test_m1_adversarial_schemas.py tests/test_challenger_m1_transport_sessions.py tests/test_challenger_m1_it2_primitives.py tests/test_challenger_m1_it2_concurrency.py tests/test_challenger_m1_hub_stdio.py tests/test_storage_isolation.py tests/test_security_and_config.py tests/test_resilience_core.py tests/test_resilience_manager.py tests/test_resilience.py tests/test_folder_security.py --basetemp=temp/pytest-release-233-qa -p no:cacheprovider
python -m pytest -q tests/test_folder_actions.py tests/test_folder_concurrent_agents.py tests/test_folder_native_safety.py tests/test_keyboard_session_assignment.py tests/test_destinations_ui.py tests/test_uia_boundaries.py tests/test_window_assignments.py tests/test_ws_agent_identity.py tests/test_ws_explicit_browser_assignment.py tests/test_ws_popup_assignment.py --basetemp=temp/pytest-release-233-qa-ui -p no:cacheprovider
```

## Limites

O gate local não prova instalador, workflow remoto, atualização em cliente
existente, nem controle de aplicações reais. Esses itens exigem evidência do
runner Windows descartável e da release publicada para o SHA final.
