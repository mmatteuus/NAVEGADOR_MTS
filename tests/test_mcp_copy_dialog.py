"""Suíte de Testes para o Diálogo de Conexão com Agentes de IA (MCPConnectDialog).

Valida a geração de JSON de configuração do MCP, cópia de prompt e rotinas de segurança.
"""

from __future__ import annotations

import json
import pytest
from src.ui.mcp_copy_dialog import MCPConnectDialog, MCP_PROMPT_TEMPLATE
from src.computer.safety_gate import safety_gate


def test_mcp_dialog_json_generation() -> None:
    """Valida que o JSON do MCP gerado contém o formato esperado para clientes MCP."""
    dialog = MCPConnectDialog.__new__(MCPConnectDialog)
    dialog.port = 3456
    raw_json = dialog._get_mcp_config_json()
    data = json.loads(raw_json)

    assert "mcpServers" in data
    assert "navegador-mts" in data["mcpServers"]
    server_cfg = data["mcpServers"]["navegador-mts"]
    assert "command" in server_cfg
    assert server_cfg["args"][-1] == "--stdio"


def test_mcp_dialog_prompt_template() -> None:
    """Valida o conteúdo do template de prompt para agentes de IA."""
    assert "ws://127.0.0.1:3456" in MCP_PROMPT_TEMPLATE
    assert "Navegador MTS" in MCP_PROMPT_TEMPLATE


def test_mcp_dialog_safety_gate_integration() -> None:
    """Valida que a demonstração visual do mouse respeita o Safety Gate."""
    safety_gate.revoke("Teste automatizado")
    assert not safety_gate.is_authorized()
    safety_gate.authorize()
    assert safety_gate.is_authorized()

