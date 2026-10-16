"""Auditoria Adversarial Tier 5 Win32: Estresse de Cursor, Modo Físico e Fail-Closed.

Comprova empiricamente:
1. Invariância absoluta do cursor do usuário (GetCursorPos) em background.
2. Funcionamento do modo físico (SendInput / Bézier) sob autorização expressa.
3. Detecção e aborto de intervenção humana física (anti-sequestro de mouse).
4. Política Fail-Closed incondicional do SafetyGate em todas as APIs.
"""
from __future__ import annotations

import ctypes
from typing import List, Tuple
from unittest.mock import patch
import pytest

from src.computer import (
    SecurityGateError, click_mouse, execute_computer_action,
    get_agent_cursor_position, get_cursor_position, move_mouse,
    post_key_press, post_keyboard_type, post_mouse_click,
    post_mouse_drag, post_mouse_move, post_mouse_scroll,
    safety_gate, type_text,
)
from src.computer.mouse_bezier import ease_in_out_cubic, generate_bezier_trajectory

user32 = ctypes.windll.user32


def test_tier5_background_zero_setcursorpos_calls(reset_safety_gate: None) -> None:
    """Verifica que funções em background nunca invocam SetCursorPos nem alteram o agente."""
    safety_gate.authorize()
    try:
        with patch.object(user32, "SetCursorPos") as mock_set_cursor:
            res_m = post_mouse_move(512, 384)
            assert res_m["background"] is True
            res_c = post_mouse_click(button="right", x=512, y=384)
            assert res_c["background"] is True
            res_d = post_mouse_drag(512, 384, 600, 450, steps=5)
            assert res_d["dragged"] is True
            res_s = post_mouse_scroll(delta_y=120, x=600, y=450)
            assert res_s["scrolled"] is True
            res_t = post_keyboard_type("Tier5-Stress-Test", delay_ms=0)
            assert res_t["background"] is True
            res_k = post_key_press("enter")
            assert res_k["background"] is True

            # Zero chamadas permitidas para SetCursorPos em operações virtuais
            assert mock_set_cursor.call_count == 0, "SetCursorPos foi invocado indevidamente!"
            assert get_agent_cursor_position() == (600, 450)
    finally:
        safety_gate.revoke("Limpeza do teste Tier 5")


def test_tier5_physical_mode_bezier_and_human_intervention(reset_safety_gate: None) -> None:
    """Valida curvas Bézier, modo físico instantâneo e detecção de intervenção física."""
    # 1. Matemática Bézier: suavização não-linear
    caminho = generate_bezier_trajectory((100, 100), (900, 700), steps=30)
    assert len(caminho) == 30
    assert caminho[-1] == (900, 700)
    assert all(isinstance(p[0], int) and isinstance(p[1], int) for p in caminho)

    # 2. Desautorizado: chamada física via execute_computer_action DEVE falhar
    res_fis = execute_computer_action("computer_mouse_move", {"x": 200, "y": 200, "background": False})
    assert res_fis["success"] is False and res_fis["isSecurityBlock"] is True

    # 3. Autorizado: modo instantâneo despacha SetCursorPos
    safety_gate.authorize()
    try:
        with patch.object(user32, "SetCursorPos", return_value=1) as mock_set:
            res_inst = move_mouse(300, 300, smooth=False)
            assert res_inst == {"currentX": 300, "currentY": 300}
            assert mock_set.call_count == 1

        # 4. Detecção de intervenção humana: se cursor físico diverge > 60px, aborta com interrupted=True
        sim_pos = [(-500, -500)]  # Cursor do usuário longe do alvo
        with patch("src.computer.mouse.get_cursor_position", side_effect=lambda: sim_pos[0]):
            with patch.object(user32, "SetCursorPos", return_value=1):
                res_interrupted = move_mouse(500, 500, smooth=True, duration_ms=50)
                assert res_interrupted.get("interrupted") is True, "Deveria abortar por intervenção física"
    finally:
        safety_gate.revoke("Fim de teste de modo físico")


def test_tier5_safety_gate_exhaustive_fail_closed(reset_safety_gate: None) -> None:
    """Comprova que 100% dos métodos são estritamente rejeitados se desautorizado."""
    assert not safety_gate.is_authorized()

    funcoes_bloqueadas = [
        (move_mouse, (10, 10)), (click_mouse, ()), (post_mouse_move, (10, 10)),
        (post_mouse_click, ()), (post_mouse_drag, (0, 0, 10, 10)),
        (post_mouse_scroll, (120,)), (type_text, ("x",)),
        (post_keyboard_type, ("x",)), (post_key_press, ("esc",))
    ]
    for fn, args in funcoes_bloqueadas:
        with pytest.raises(SecurityGateError):
            fn(*args)

    # Ações despachadas
    for act in ["mouse_move", "mouse_click", "mouse_drag", "mouse_scroll", "keyboard_type", "key_press"]:
        res_bg = execute_computer_action(f"computer_{act}", {"x": 10, "y": 10, "text": "t", "key": "k", "background": True})
        assert res_bg["success"] is False and res_bg["isSecurityBlock"] is True
        res_ph = execute_computer_action(f"computer_{act}", {"x": 10, "y": 10, "text": "t", "key": "k", "background": False})
        assert res_ph["success"] is False and res_ph["isSecurityBlock"] is True
