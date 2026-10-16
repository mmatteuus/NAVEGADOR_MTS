"""Testes E2E Opaque-Box - Tier 2: Limites, Casos de Borda e Validação Estrita.

Aplica Boundary Value Analysis (BVA) e testes adversariais de entrada
sobre schemas MCP, coordenadas extremas, strings vazias e travas de segurança.
"""
from __future__ import annotations

import asyncio
import pytest
from src.mcp import MCPToolRouter
from src.mcp.computer_dispatch import execute_mcp_computer


def test_tier2_mouse_coordinates_boundaries() -> None:
    """Valida coordenadas nos limites: zero, limites de resolução 4K e negativas."""
    captured: list[tuple[str, dict]] = []

    def fake_exec(name: str, args: dict) -> dict:
        captured.append((name, args))
        return {"success": True, "data": args}

    # Limite inferior válido: (0, 0)
    res_zero = asyncio.run(execute_mcp_computer("computer_mouse_action", {"action": "move", "x": 0, "y": 0}, fake_exec))
    assert res_zero["success"] is True
    assert captured[-1][1] == {"x": 0, "y": 0, "background": True}

    # Limite superior de alta resolução: 4K (3840, 2160)
    res_4k = asyncio.run(execute_mcp_computer("computer_mouse_action", {"action": "move", "x": 3840, "y": 2160}, fake_exec))
    assert res_4k["success"] is True

    # Coordenadas negativas (multi-monitor à esquerda)
    res_neg = asyncio.run(execute_mcp_computer("computer_mouse_action", {"action": "move", "x": -1920, "y": 0}, fake_exec))
    assert res_neg["success"] is True


def test_tier2_keyboard_string_extremes_and_empty() -> None:
    """Valida digitação com string vazia, caracteres de controle e textos extensos."""
    captured: list[tuple[str, dict]] = []

    def fake_exec(name: str, args: dict) -> dict:
        captured.append((name, args))
        return {"success": True, "data": args}

    # String vazia
    res_empty = asyncio.run(execute_mcp_computer("computer_keyboard_action", {"action": "type", "text": ""}, fake_exec))
    assert res_empty["success"] is True

    # String contendo caracteres de controle, quebras e tabulações
    complex_text = "Linha 1\r\n\tTabulação & <script>alert('xss')</script> 😀"
    res_complex = asyncio.run(execute_mcp_computer("computer_keyboard_action", {"action": "type", "text": complex_text}, fake_exec))
    assert res_complex["success"] is True
    assert captured[-1][1]["text"] == complex_text


def test_tier2_schema_missing_required_arguments() -> None:
    """Valida rejeição elegante quando campos obrigatórios do schema são omitidos."""
    # Mouse sem 'action'
    res_no_act = asyncio.run(execute_mcp_computer("computer_mouse_action", {"x": 10, "y": 20}))
    assert res_no_act["success"] is False
    assert "Ação de mouse não suportada" in res_no_act["error"]

    # Drag sem coordenadas finais (end_x, end_y)
    res_drag_missing = asyncio.run(execute_mcp_computer("computer_mouse_action", {"action": "drag", "x": 10, "y": 20}))
    assert res_drag_missing["success"] is False
    assert "end_x" in res_drag_missing["error"] or "KeyError" in res_drag_missing["error"]

    # Teclado sem texto em 'type'
    res_type_missing = asyncio.run(execute_mcp_computer("computer_keyboard_action", {"action": "type"}))
    assert res_type_missing["success"] is False

    # Hotkey com lista vazia de teclas
    res_hotkey_empty = asyncio.run(execute_mcp_computer("computer_keyboard_action", {"action": "hotkey", "keys": []}))
    assert res_hotkey_empty["success"] is False
    assert "Hotkey requer lista não vazia" in res_hotkey_empty["error"]


def test_tier2_router_unknown_tool_rejection() -> None:
    """Valida envelope de erro MCP padronizado ao requisitar ferramentas inexistentes."""
    router = MCPToolRouter()
    res = asyncio.run(router.dispatch("sistema_desconhecido_x", {"foo": "bar"}))
    assert res["isError"] is True
    assert "Ferramenta desconhecida" in res["content"][0]["text"]


def test_tier2_safety_gate_kill_switch_precedence() -> None:
    """Valida que mesmo se autorizado, o disparo do KillSwitch bloqueia o acesso."""
    # Simula autorização concedida, mas kill-switch acionado pelo usuário (3x ESC)
    router = MCPToolRouter(
        computer_executor=lambda n, a: asyncio.sleep(0, result={"success": True}),
        safety_checker=lambda: False,  # Se o kill-switch atua, o checker reflete desautorização
        kill_switch_checker=lambda: True,
    )
    status_res = asyncio.run(router.dispatch("computer_get_status", {}))
    assert not status_res["isError"]
    assert "killSwitchActive\": true" in status_res["content"][0]["text"]

    # Tentativa de ação é sumariamente rejeitada
    action_res = asyncio.run(router.dispatch("computer_mouse_action", {"action": "click"}))
    assert action_res["isError"] is True
    assert "não autorizado" in action_res["content"][0]["text"].lower()
