"""Testes adversariais de contratos e isolamento de Schemas MCP (M1 Challenger 2).

Valida integridade formal de schemas, rejeição estrita de ações desconhecidas,
aceite completo de scroll e bloqueio fail-closed no roteamento.
"""
from __future__ import annotations

import json
import pytest
from src.mcp.schemas_computer import get_computer_tools
from src.mcp.schemas_browser import get_browser_tools
from src.mcp.computer_dispatch import _plan, execute_mcp_computer
from src.mcp.router import MCPToolRouter


def test_schemas_formal_integrity_and_uniqueness() -> None:
    """Verifica unicidade, prefixos, serialização e conformidade JSON Schema."""
    comp_tools = get_computer_tools()
    brow_tools = get_browser_tools()
    all_tools = comp_tools + brow_tools

    names = [t["name"] for t in all_tools]
    assert len(names) == len(set(names)), "Existem nomes de ferramentas duplicados"
    assert len(all_tools) == 17, f"Esperado exatamente 17 ferramentas MCP, obtido {len(all_tools)}"
    assert "computer_folder_action" in [tool["name"] for tool in all_tools]
    assert "computer_window_action" in names

    for tool in all_tools:
        assert tool["name"].startswith(("computer_", "browser_"))
        assert "description" in tool and len(tool["description"]) > 5
        schema = tool.get("inputSchema", {})
        assert schema.get("type") == "object"
        assert isinstance(schema.get("properties"), dict)
        if "required" in schema:
            assert isinstance(schema["required"], list)
            for req in schema["required"]:
                assert req in schema["properties"], f"Campo required '{req}' ausente em properties de {tool['name']}"
        dumped = json.dumps(tool)
        assert len(dumped) > 20


@pytest.mark.asyncio
async def test_computer_dispatch_rejects_unknown_and_malformed() -> None:
    """Valida rejeição estrita de ferramentas e ações inexistentes ou malformadas."""
    with pytest.raises(ValueError, match="desconhecida"):
        _plan("computer_invalid_tool", {})
    with pytest.raises(ValueError, match="objeto JSON"):
        _plan("computer_mouse_action", "nao_e_dict")  # type: ignore

    for bad_action in ["fly", "hover_click", "", None, 999]:
        with pytest.raises(ValueError, match="não suportada"):
            _plan("computer_mouse_action", {"action": bad_action})

    for bad_kbd in ["sing", "whistle", "", None]:
        with pytest.raises(ValueError, match="não suportada"):
            _plan("computer_keyboard_action", {"action": bad_kbd})

    with pytest.raises(ValueError, match="Hotkey requer lista não vazia"):
        _plan("computer_keyboard_action", {"action": "hotkey", "keys": []})
    with pytest.raises(ValueError, match="Hotkey requer lista não vazia"):
        _plan("computer_keyboard_action", {"action": "hotkey", "keys": "ctrl+c"})

    # execute_mcp_computer deve capturar e retornar envelope seguro de erro
    res = await execute_mcp_computer("computer_mouse_action", {"action": "teleport"})
    assert res["success"] is False
    assert "Argumentos inválidos" in res["error"]


@pytest.mark.asyncio
async def test_computer_dispatch_accepts_scroll_and_parameters() -> None:
    """Verifica aceitação completa de scroll com variações de delta, background e hwnd."""
    p0 = _plan("computer_mouse_action", {"action": "scroll"})
    assert len(p0) == 1 and p0[0][0] == "computer_mouse_scroll"
    assert p0[0][1]["deltaY"] == 0 and p0[0][1]["delta"] == 0

    p1 = _plan("computer_mouse_action", {
        "action": "scroll", "delta": 360, "background": True, "hwnd": 9912
    })
    assert p1[0][1]["deltaY"] == 360 and p1[0][1]["background"] is True and p1[0][1]["hwnd"] == 9912

    p2 = _plan("computer_mouse_action", {
        "action": "scroll", "delta": -120, "delta_x": 45, "background": False
    })
    assert p2[0][1]["deltaY"] == -120 and p2[0][1]["deltaX"] == 45 and p2[0][1]["background"] is False

    captured = []
    def fake_executor(op: str, params: dict) -> dict:
        captured.append((op, params))
        return {"success": True, "data": {"scrolled": True}}

    res = await execute_mcp_computer("computer_mouse_action", {"action": "scroll", "delta": 100}, executor=fake_executor)
    assert res["success"] is True and len(captured) == 1 and captured[0][0] == "computer_mouse_scroll"


@pytest.mark.asyncio
async def test_router_adversarial_dispatch_and_fail_closed() -> None:
    """Valida bloqueio fail-closed da Trava de Segurança e rejeição de rotas desconhecidas."""
    router = MCPToolRouter()
    res_unknown = await router.dispatch("unknown_system_exec", {"cmd": "calc"})
    assert res_unknown["isError"] is True
    assert "Ferramenta desconhecida" in res_unknown["content"][0]["text"]

    locked_router = MCPToolRouter(safety_checker=lambda: False)
    res_mouse = await locked_router.dispatch("computer_mouse_action", {"action": "scroll", "delta": 100})
    assert res_mouse["isError"] is True
    assert "Ação recusada: Controle do Computador não autorizado" in res_mouse["content"][0]["text"]

    res_status = await locked_router.dispatch("computer_get_status", {})
    assert res_status["isError"] is False
    status_data = json.loads(res_status["content"][0]["text"])
    assert status_data["authorized"] is False

    res_browser = await locked_router.dispatch("browser_scroll", {"direction": "down"})
    assert res_browser["isError"] is True
    assert "A extensão do navegador não está conectada" in res_browser["content"][0]["text"]
