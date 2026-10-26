# 📐 07. Guia de Modularidade, Boas Práticas e Versionamento (v2.4.0)

## 1. O Mandamento Inegociável: Arquivos Pequenos ($\le 150$ LOC)

A base de código do **NAVEGADOR MTS** rejeita terminantemente arquivos monolíticos. Cada componente em `src/` e cada arquivo de teste em `tests/` é estruturado de forma cirúrgica com responsabilidade única:

> 📌 **Regra de Ouro**: Nenhum arquivo (`.py`, `.js`, `.css`, `.html`) pode ultrapassar **150 linhas de código (LOC)**. Se um arquivo se aproximar desse limite, deve ser dividido imediatamente em sub-módulos coesos.

---

## 2. Padrão Real de Código e Documentação (Python + JS MV3)

Todo arquivo do projeto deve ser escrito e documentado em **Português do Brasil**, utilizando `from __future__ import annotations` e type hints claros no Python:

```python
"""Módulo de exemplo demonstrando o padrão oficial do NAVEGADOR MTS.

Responsabilidades:
- Validação obrigatória do SafetyGate (Fail-Closed) antes de ações físicas.
- Código enxuto, tipado e com <= 150 linhas.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from ..computer.safety_gate import safety_gate

logger = logging.getLogger("BrowserMTS.Example")


async def execute_safe_action(action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Executa uma ação somente se o SafetyGate estiver explicitamente autorizado."""
    safety_gate.check_authorization(action_name)
    logger.info(f"Executando {action_name} com segurança.")
    return {"success": True, "action": action_name}
```

---

## 3. Filosofia "Pensar à Frente" (Engenharia Defensiva)

Ao desenvolver qualquer melhoria, avalie sempre os efeitos em cascata:

| Ação Primária | Erro em Cascata em Potencial | Solução Preventiva Implementada no NAVEGADOR MTS |
| :--- | :--- | :--- |
| Subir WebSocket Bridge na porta `3456` | Porta `3456` ocupada ou colisão com HTTP `3457` | `WebSocketBridge.start()` e `port_recovery.js` testam `3456..3465` **pulando `3457`** |
| Múltiplos agentes Stdio conectando juntos | Segundo processo Stdio falhar ao tentar abrir a porta `3456` | `hub_client.py` detecta o Hub ativo e encaminha `tools/call` via WebSocket com `sessionId` próprio |
| Dois agentes clicando ao mesmo tempo | Condição de corrida em abas, janelas ou mouse físico | `ExecutionCoordinator` aplica locks por `tab:<id>`, `hwnd:<id>` e `physical_input` |
| Consulta de atualização na API GitHub | GitHub REST API retornar HTTP 403 (Rate Limit sem token) | `update_web_fallback.py` resolve a tag e o asset `.exe` via redirecionamento web público |
| Instalador atualizando binários em uso | Fechar processos `python.exe` ou `tunnel-client.exe` de outros projetos | `installer/close_owned_processes.ps1` filtra exclusivamente pelo caminho absoluto da pasta instalada |
| Agente acessando pasta local autorizada | Escape de diretório via symlink, junction ou hardlink | `LockedHandle` (`folder_handles.py`) bloqueia `FILE_ATTRIBUTE_REPARSE_POINT` e confere `GetFinalPathNameByHandleW` |

---

## 4. Protocolo Padronizado de Versionamento e Release

Toda melhoria ou correção realizada no repositório deve seguir o fluxo padronizado de release:

1. **Sincronizar a Versão (`release_version.py`)**:
   ```powershell
   python release_version.py --set 2.4.0
   # ou incrementar patch:
   python release_version.py --bump patch
   ```
   Isso atualiza atomicamente `src/version.py`, `src/extension/manifest.json` e `installer.iss`.
2. **Rodar as Suítes de Teste (Python + Node)**:
   ```powershell
   python -m pytest -q
   node tests/run_extension_suite.mjs
   ```
3. **Compilar Executáveis e Instalador Oficial**:
   ```powershell
   .\COMPILAR_INSTALADOR.bat
   ```
   Gera `dist_installer\NAVEGADOR_MTS_Instalador_v<VERSAO>.exe`.
4. **Atualizar o Cérebro no Obsidian**:
   Registre o avanço em `D:\MATEUS\Documentos\GitHub\Obsidian\Vault\02-PROJECTS\NAVEGADOR_MTS\01-HANDOFF-VIVO.md`.
