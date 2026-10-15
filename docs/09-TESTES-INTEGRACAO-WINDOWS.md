# Validação isolada do NAVEGADOR MTS — Windows

## Componentes desta aplicação

- Desktop: `NAVEGADOR_MTS.exe` (CustomTkinter/Win32)
- Extensão Manifest V3 própria: `src/extension`
- MCP WebSocket local: `127.0.0.1:3456` (fallback ignora 3457)
- MCP HTTP local: `http://127.0.0.1:3457/mcp`
- Secure MCP Tunnel: `tunnel-client.exe` (processo separado)
- MCP Stdio instalado: `mcp_stdio/NAVEGADOR_MTS_MCP.exe`

Um conector pré-existente com nome semelhante no ChatGPT **não valida este aplicativo**.
Não use outras integrações para verificar este repositório.

## Verificação sem alterar produção

1. Acesse GitHub > Actions > **QA Windows e instalador**.
2. Exija sucesso dos jobs de contratos e instalador.
3. Baixe o artefato `Navegador-MTS-Windows-Teste`.
4. Salve o instalador anterior como rollback; interrompa o novo NAVEGADOR MTS.
5. Execute o instalador gerado (mantém AppId e diretório da aplicação).
6. Execute com o aplicativo aberto:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\TESTAR_INTEGRACAO.ps1
```

Para iniciar o app instalado, use `-StartApp`.

## Critérios de aceite

- `GET /healthz` retorna `service=browser-mcp-mts`.
- `initialize` e `tools/list` respondem a POST `/mcp`.
- `computer_get_status` representa o SafetyGate.
- WebSocket na porta 3456 ou fallback, nunca 3457.
- Extensão própria conecta; `browser_navigate` conclui.
- Túnel local aponta para `127.0.0.1:3457/mcp`, com credenciais configuradas.
- `tunnel-client` informa readiness pelo endpoint local `/readyz`.
- ChatGPT descobre ferramentas da nova conexão.
- Reinstalação preserva dados em `%APPDATA%\browser-mcp-mts`.
- Nenhum executável ou perfil do legado foi alterado.

## Rollback

Execute o instalador anterior salvo, mantendo dados locais.
O smoke test não move mouse, não digita e não captura tela.
