"""Regressão dos esquemas Computer Use e da política fail-closed."""
from __future__ import annotations

import asyncio
import json
import sys
from types import ModuleType
from unittest.mock import patch
import pytest

from src.mcp.computer_dispatch import _plan, execute_mcp_computer
from src.mcp.router import MCPToolRouter


def test_mapping_mouse_keyboard_and_screenshot():
    """Cada opção anunciada deve ter ação nativa equivalente."""
    assert _plan("computer_mouse_action", {"action": "move", "x": 2, "y": 3}) == [
        ("computer_mouse_move", {"x": 2, "y": 3, "background": True})]
    assert _plan("computer_mouse_action", {"action": "double_click"})[0][1]["double"]
    assert _plan("computer_mouse_action", {"action": "drag", "x": 1, "y": 2,
                                          "end_x": 3, "end_y": 4})[0][1]["endX"] == 3
    assert _plan("computer_keyboard_action", {"action": "hotkey",
                                               "keys": ["ctrl", "a"]})[0][1] == {
        "key": "a", "modifiers": ["ctrl"], "background": True}
    assert _plan("computer_screenshot", {}) == [("computer_screenshot", {})]


def test_invalid_command_never_executes():
    """Nenhum mouse é movimentado com ação incompleta."""
    calls = []

    def fake(name, args):
        calls.append(name)
        return {"success": True, "data": {"ok": True}}

    result = asyncio.run(execute_mcp_computer(
        "computer_mouse_action", {"action": "drag", "x": 1, "y": 2}, fake))
    assert result["success"] is False
    assert calls == []


def test_executor_failure_stops_following_actions():
    """Se mover o mouse falhar, não enviar clique."""
    calls = []

    def fail_first(name, args):
        calls.append(name)
        return {"success": False, "error": "ERRO_SEGURANCA"}

    result = asyncio.run(execute_mcp_computer(
        "computer_mouse_action", {"action": "click", "x": 3, "y": 4}, fail_first))
    assert result["success"] is False
    assert calls == ["computer_mouse_move"]


def test_execute_mcp_computer_non_dict_args_and_exceptions():
    """Valida argumentos não-dicionário e captura de exceções."""
    res1 = asyncio.run(execute_mcp_computer("computer_get_status", "invalid_args", executor=lambda n, a: {}))
    assert res1["success"] is False
    assert "Argumentos MCP devem ser um objeto JSON" in res1["error"]

    res2 = asyncio.run(execute_mcp_computer("unknown_tool", {}, executor=lambda n, a: {}))
    assert res2["success"] is False
    assert "Ferramenta de computador desconhecida" in res2["error"]


def test_execute_mcp_computer_folder_action_routing():
    """Despacho de ações de pasta via execute_folder_action."""
    folder_mod = ModuleType("src.computer.folder_actions")
    called_args = []

    def fake_execute(args, sid):
        called_args.append((args, sid))
        return {"success": True, "files": []}

    folder_mod.execute_folder_action = fake_execute

    with patch.dict("sys.modules", {"src.computer.folder_actions": folder_mod}), \
         patch("src.mcp.session_context.get_current_session_id", return_value="sess_ctx"):
        res = asyncio.run(execute_mcp_computer("computer_folder_action", {"sessionId": "sess_arg"}))
        assert res == {"success": True, "files": []}
        assert called_args == [({"sessionId": "sess_arg"}, "sess_ctx")]


def test_execute_mcp_computer_default_executor_and_multi_op():
    """Uso do executor padrão nativo e encadeamento multi-operação com sucesso."""
    calls = []

    def multi_fake(op, params):
        calls.append(op)
        return {"success": True, "op": op}

    res_multi = asyncio.run(execute_mcp_computer("computer_mouse_action", {"action": "click", "x": 10, "y": 20}, multi_fake))
    assert res_multi == {"success": True, "op": "computer_mouse_click"}
    assert calls == ["computer_mouse_move", "computer_mouse_click"]

    comp_mod = ModuleType("src.computer")
    comp_mod.execute_computer_action = lambda op, params: {"success": True, "op": op}
    with patch.dict("sys.modules", {"src.computer": comp_mod}):
        res_default = asyncio.run(execute_mcp_computer("computer_get_status", {}))
        assert res_default == {"success": True, "op": "computer_get_status"}


def test_router_rejects_when_gate_closed_and_handles_images():
    """Permissão e imagens devem seguir o contrato MCP."""
    async def run():
        calls = []

        async def fake(name, args):
            calls.append(name)
            return {"success": True, "data": {"imageBase64": "AA==",
                                             "format": "png", "width": 1}}

        router = MCPToolRouter(computer_executor=fake, safety_checker=lambda: False)
        forbidden = await router.dispatch("computer_screenshot", {})
        assert forbidden["isError"] is True
        assert calls == []
        allowed = MCPToolRouter(computer_executor=fake, safety_checker=lambda: True)
        screenshot = await allowed.dispatch("computer_screenshot", {})
        assert screenshot["isError"] is False
        assert screenshot["content"][0]["type"] == "image"
        assert screenshot["content"][0]["data"] == "AA=="
        status = await router.dispatch("computer_get_status", {})
        assert json.loads(status["content"][0]["text"])["authorized"] is False
    asyncio.run(run())
