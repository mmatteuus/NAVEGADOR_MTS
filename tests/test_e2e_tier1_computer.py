"""Testes E2E Opaque-Box - Tier 1: Cobertura de Funcionalidades Desktop.

Valida os contratos MCP de automação do Windows 11 (computer_*):
status de autorização, mouse, teclado, captura de tela e lançamento de apps.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from src.mcp import MCPServer, MCPToolRouter
from src.mcp.computer_dispatch import execute_mcp_computer


class MockWin32Executor:
    """Simulador de execução nativa para testes de contrato Opaque-Box."""

    def __init__(self) -> None:
        self.invoked_ops: list[tuple[str, dict]] = []

    def __call__(self, operation: str, params: dict) -> dict:
        self.invoked_ops.append((operation, dict(params)))
        if operation == "computer_screenshot":
            return {"success": True, "data": {"base64": "UklGRkIAAABXRUJQ", "format": "png"}}
        if operation == "computer_launch_app":
            return {"success": True, "data": {"app": params.get("app"), "pid": 4500}}
        return {"success": True, "data": {"operation": operation, "status": "executed"}}


def test_tier1_computer_status_contract() -> None:
    """Valida retorno do status de segurança sem exigir autorização prévia."""
    router = MCPToolRouter(safety_checker=lambda: False, kill_switch_checker=lambda: False)
    res = asyncio.run(router.dispatch("computer_get_status", {}))
    assert not res["isError"]
    payload = json.loads(res["content"][0]["text"])
    assert payload["authorized"] is False
    assert payload["killSwitchActive"] is False


def test_tier1_computer_mouse_actions_planning() -> None:
    """Valida o mapeamento de ações de mouse para operações nativas Win32."""
    executor = MockWin32Executor()
    # 1. Movimento
    res_move = asyncio.run(execute_mcp_computer("computer_mouse_action", {"action": "move", "x": 100, "y": 200}, executor))
    assert res_move.get("success") is True
    # 2. Clique duplo
    res_dbl = asyncio.run(execute_mcp_computer("computer_mouse_action", {"action": "double_click", "x": 50, "y": 50}, executor))
    assert res_dbl.get("success") is True
    # 3. Arrasto (drag)
    res_drag = asyncio.run(execute_mcp_computer(
        "computer_mouse_action", {"action": "drag", "x": 10, "y": 20, "end_x": 100, "end_y": 200}, executor
    ))
    assert res_drag.get("success") is True
    assert any(op[0] == "computer_mouse_drag" for op in executor.invoked_ops)


def test_tier1_computer_keyboard_actions_unicode() -> None:
    """Valida envio de texto Unicode (ABNT2), tecla e atalhos combinados."""
    executor = MockWin32Executor()
    # Digitação de texto com acentuação e cedilha
    res_type = asyncio.run(execute_mcp_computer(
        "computer_keyboard_action", {"action": "type", "text": "Atenção: Ação Automatizada Ç!"}, executor
    ))
    assert res_type.get("success") is True
    # Envio de tecla individual
    res_press = asyncio.run(execute_mcp_computer("computer_keyboard_action", {"action": "press", "key": "Return"}, executor))
    assert res_press.get("success") is True
    # Envio de hotkey (atalho com modificador)
    res_hotkey = asyncio.run(execute_mcp_computer(
        "computer_keyboard_action", {"action": "hotkey", "keys": ["Control", "Shift", "s"]}, executor
    ))
    assert res_hotkey.get("success") is True
    assert executor.invoked_ops[-1] == (
        "computer_key_press", {"key": "s", "modifiers": ["Control", "Shift"], "background": True}
    )


def test_tier1_computer_screenshot_and_launch(dynamic_port: int) -> None:
    """Valida ferramentas de screenshot e lançamento de app com SafetyGate ativo."""
    executor = MockWin32Executor()
    router = MCPToolRouter(
        computer_executor=lambda name, args: asyncio.sleep(0, result=executor(name, args)),
        safety_checker=lambda: True,
    )
    # Screenshot do Windows
    res_shot = asyncio.run(router.dispatch("computer_screenshot", {"format": "png"}))
    assert not res_shot["isError"]
    assert res_shot["content"][0]["type"] == "image"
    # Lançamento de aplicativo local
    res_app = asyncio.run(router.dispatch("computer_launch_app", {"app": "notepad"}))
    assert not res_app["isError"]
    assert "notepad" in res_app["content"][0]["text"]


def test_tier1_computer_fail_closed_blocking() -> None:
    """Garante que router bloqueia qualquer ação computer_* sem autorização explícita."""
    executor = MockWin32Executor()
    router = MCPToolRouter(
        computer_executor=lambda name, args: asyncio.sleep(0, result=executor(name, args)),
        safety_checker=lambda: False,
    )
    res = asyncio.run(router.dispatch("computer_mouse_action", {"action": "click", "x": 50, "y": 50}))
    assert res["isError"] is True
    assert "não autorizado" in res["content"][0]["text"].lower()
    assert len(executor.invoked_ops) == 0
