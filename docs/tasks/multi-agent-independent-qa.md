# QA independente — 2026-10-25

Escopo: contratos MCP, roteamento WebSocket, isolamento de sessões, atualização,
schemas, storage, resiliência, extensão MV3 e arquivos concedidos. Execução sem
mouse/teclado físico, foco de janela, screenshot do desktop, launch de programa,
kill-switch global ou dados pessoais.

Comandos executados:

```text
python -m pytest -q tests/test_mcp_protocol.py tests/test_mcp_http.py tests/test_mcp_ws_bridge.py tests/test_mcp_ws_multisession.py tests/test_multisession_concurrency.py tests/test_ws_extension_routing.py tests/test_ws_response_ownership.py tests/test_agent_directory.py tests/test_agent_actions_ws.py tests/test_m1_refactoring_and_schemas.py tests/test_m1_adversarial_schemas.py tests/test_challenger_m1_transport_sessions.py tests/test_challenger_m1_it2_primitives.py tests/test_challenger_m1_it2_concurrency.py tests/test_challenger_m1_hub_stdio.py tests/test_storage_isolation.py tests/test_security_and_config.py tests/test_resilience_core.py tests/test_resilience_manager.py tests/test_resilience.py tests/test_folder_security.py --basetemp=temp/pytest-safe-broad-20261025c -p no:cacheprovider
node tests/run_extension_suite.mjs
python -m pytest -q tests/test_folder_security.py --basetemp=temp/pytest-folder-security-junction-20261025 -p no:cacheprovider
```

Resultados atuais: suíte Node `19 testes passaram`; seleção Python ampla
`76 passed, 1 skipped` (3,00 s); segurança de pastas `7 passed, 1 skipped`
(symlink comum indisponível). O teste de Computer Use agora registra a identidade
no handshake, confirma `TARGET_NOT_ASSIGNED` sem atribuição e confirma o caminho
positivo com executor simulado, sem ação física.

As provas não demonstram cliente final instalado, atualização física do navegador,
buffers não salvos do VS Code, nem controle de programas reais. Esses gates ficam
separados de testes locais e exigem ambiente descartável autorizado.
