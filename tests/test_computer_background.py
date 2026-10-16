"""Suíte de Testes Unitários para Mouse e Teclado em Background no Windows.

Valida que as operações virtuais de segundo plano não movem o cursor físico
(GetCursorPos), respeitam a trava Fail-Closed do SafetyGate, suportam scroll,
drag, resolução de janela (ScreenToClient) e digitação sem roubo de foco.
"""

from __future__ import annotations

import pytest
from src.computer import (
    SecurityGateError, execute_computer_action, find_window_at,
    get_agent_cursor_position, get_cursor_position, post_key_press,
    post_keyboard_type, post_mouse_click, post_mouse_drag,
    post_mouse_move, post_mouse_scroll, resolve_target_window,
    safety_gate, screen_to_client,
)


def test_background_mouse_does_not_alter_physical_cursor(reset_safety_gate: None) -> None:
    """Garante que comandos virtuais em background jamais movem o cursor físico GetCursorPos."""
    safety_gate.authorize()
    try:
        cur_antes = get_cursor_position()
        res_move = execute_computer_action("computer_mouse_move", {"x": 800, "y": 600, "background": True})
        assert res_move["success"] is True and res_move["data"]["background"] is True
        cur_depois_move = get_cursor_position()
        assert cur_antes == cur_depois_move, "GetCursorPos físico não pode ser alterado por mouse_move background"

        res_click = execute_computer_action("computer_mouse_click", {"button": "left", "background": True})
        assert res_click["success"] is True and res_click["data"]["background"] is True
        assert cur_antes == get_cursor_position(), "GetCursorPos físico deve permanecer intacto após clique"

        ax, ay = get_agent_cursor_position()
        assert (ax, ay) == (800, 600), "Cursor virtual do agente deve registrar (800, 600)"
    finally:
        safety_gate.revoke("Fim do teste de isolamento de cursor")


def test_background_actions_fail_closed_without_authorization(reset_safety_gate: None) -> None:
    """Verifica que qualquer ação em background é estritamente bloqueada pelo SafetyGate desautorizado."""
    assert not safety_gate.is_authorized(), "SafetyGate deve iniciar desautorizado por padrão"

    res_move = execute_computer_action("computer_mouse_move", {"x": 100, "y": 100, "background": True})
    assert res_move["success"] is False and res_move.get("isSecurityBlock") is True

    res_type = execute_computer_action("computer_keyboard_type", {"text": "bloqueado", "background": True})
    assert res_type["success"] is False and res_type.get("isSecurityBlock") is True

    with pytest.raises(SecurityGateError):
        post_mouse_move(100, 100)
    with pytest.raises(SecurityGateError):
        post_mouse_click("left")
    with pytest.raises(SecurityGateError):
        post_mouse_scroll(delta_y=120)
    with pytest.raises(SecurityGateError):
        post_keyboard_type("texto")
    with pytest.raises(SecurityGateError):
        post_key_press("Enter")


def test_window_finder_and_coordinate_resolution() -> None:
    """Valida a resolução de hwnd e a conversão de tela para coordenadas da janela cliente."""
    hwnd = find_window_at(100, 100)
    assert isinstance(hwnd, int) and hwnd > 0, "Deve encontrar um hwnd válido ou o DesktopWindow"

    cx, cy = screen_to_client(hwnd, 100, 100)
    assert isinstance(cx, int) and isinstance(cy, int), "ScreenToClient deve retornar coordenadas inteiras"

    target_hwnd, rx, ry = resolve_target_window(200, 200)
    assert target_hwnd > 0 and isinstance(rx, int) and isinstance(ry, int)

    explicit_hwnd, ex_cx, ex_cy = resolve_target_window(150, 150, hwnd=hwnd)
    assert explicit_hwnd == hwnd and isinstance(ex_cx, int) and isinstance(ex_cy, int)


def test_background_scroll_and_drag(reset_safety_gate: None) -> None:
    """Valida rolagem de scroll e arraste suave em background sem mover cursor físico."""
    safety_gate.authorize()
    try:
        pos_antes = get_cursor_position()
        res_scroll = execute_computer_action(
            "computer_mouse_scroll", {"delta": 120, "x": 300, "y": 300, "background": True}
        )
        assert res_scroll["success"] is True and res_scroll["data"]["scrolled"] is True

        res_drag = execute_computer_action(
            "computer_mouse_drag",
            {"startX": 200, "startY": 200, "endX": 350, "endY": 350, "steps": 3, "background": True}
        )
        assert res_drag["success"] is True and res_drag["data"]["dragged"] is True
        assert get_cursor_position() == pos_antes, "Cursor físico deve permanecer inalterado após scroll e drag"
    finally:
        safety_gate.revoke("Fim do teste de scroll/drag")


def test_background_keyboard_dispatch(reset_safety_gate: None) -> None:
    """Valida envio de digitação Unicode e teclas virtuais em background."""
    safety_gate.authorize()
    try:
        res_type = execute_computer_action(
            "computer_keyboard_type", {"text": "Ação Virtu@l 123", "background": True}
        )
        assert res_type["success"] is True and res_type["data"]["typedChars"] == len("Ação Virtu@l 123")
        assert res_type["data"]["background"] is True

        res_press = execute_computer_action(
            "computer_key_press", {"key": "Tab", "modifiers": ["shift"], "background": True}
        )
        assert res_press["success"] is True and res_press["data"]["executedKey"] == "Tab"
        assert res_press["data"]["modifiers"] == ["shift"]
    finally:
        safety_gate.revoke("Fim do teste de teclado")
