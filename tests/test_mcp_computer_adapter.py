"""Regressão dos esquemas Computer Use e da política fail-closed."""
from __future__ import annotations

import asyncio
import json
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


def test_is_computer_authorized_direct():
    """Valida o comportamento direto de is_computer_authorized para autorização, negação e exceções."""
    # Safety checker autorizando
    router_authorized = MCPToolRouter(safety_checker=lambda: True)
    assert router_authorized.is_computer_authorized() is True

    # Safety checker negando
    router_denied = MCPToolRouter(safety_checker=lambda: False)
    assert router_denied.is_computer_authorized() is False

    # Safety checker padrão (None fornecido na inicialização)
    router_default = MCPToolRouter()
    assert router_default.is_computer_authorized() is False

    # Safety checker lançando exceção (deve capturar e retornar False / fail-closed)
    def failing_checker():
        raise RuntimeError("Erro ao verificar segurança")

    router_exception = MCPToolRouter(safety_checker=failing_checker)
    assert router_exception.is_computer_authorized() is False

    # Safety checker retornando valores truthy / falsy não-booleanos
    router_truthy = MCPToolRouter(safety_checker=lambda: 1)
    assert router_truthy.is_computer_authorized() is True

    router_falsy = MCPToolRouter(safety_checker=lambda: None)
    assert router_falsy.is_computer_authorized() is False
