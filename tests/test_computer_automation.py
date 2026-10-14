"""Suíte de Testes para o Módulo de Computer Use do BROWSER MTS.

Valida automação do Windows: curvas Bézier, cliques/scroll, digitação
Unicode ABNT2, captura multi-monitor e despachante com trava Fail-Closed.
"""

from __future__ import annotations

import pytest
from src.computer import (
    SecurityGateError, capture_screen, click_mouse, drag_mouse,
    execute_computer_action, get_cursor_position, get_monitors_info,
    move_mouse, press_key, release_all_keys, release_mouse_buttons,
    safety_gate, scroll_mouse, type_text,
)
from src.computer.mouse_bezier import (
    cubic_bezier_point, ease_in_out_cubic, generate_bezier_trajectory,
)


def test_mouse_bezier_math():
    """Valida a precisão matemática da interpolação Bézier e das curvas de easing."""
    assert ease_in_out_cubic(0.0) == pytest.approx(0.0)
    assert ease_in_out_cubic(1.0) == pytest.approx(1.0)
    assert ease_in_out_cubic(0.5) == pytest.approx(0.5)

    p0, p1, p2, p3 = (0.0, 0.0), (10.0, 20.0), (80.0, 90.0), (100.0, 100.0)
    assert cubic_bezier_point(p0, p1, p2, p3, 0.0) == (0, 0)
    assert cubic_bezier_point(p0, p1, p2, p3, 1.0) == (100, 100)

    path = generate_bezier_trajectory((100, 100), (500, 400), steps=20)
    assert len(path) == 20
    assert path[-1] == (500, 400)


def test_computer_use_blocked_when_unauthorized(reset_safety_gate):
    """Garante que ações de mouse, teclado e tela são estritamente rejeitadas se desautorizado."""
    assert not safety_gate.is_authorized()
    with pytest.raises(SecurityGateError):
        move_mouse(100, 100)
    with pytest.raises(SecurityGateError):
        click_mouse("left")
    with pytest.raises(SecurityGateError):
        drag_mouse(0, 0, 100, 100)
    with pytest.raises(SecurityGateError):
        scroll_mouse(delta_y=120)
    with pytest.raises(SecurityGateError):
        type_text("Texto bloqueado")
    with pytest.raises(SecurityGateError):
        press_key("a")
    with pytest.raises(SecurityGateError):
        capture_screen()


def test_execute_computer_action_fail_closed(reset_safety_gate):
    """Valida o envelope de resposta padronizado em caso de bloqueio de segurança."""
    res = execute_computer_action("computer_mouse_click", {"button": "left"})
    assert res["success"] is False and res.get("isSecurityBlock") is True
    assert "ERRO_SEGURANCA" in res["error"]

    status = execute_computer_action("computer_get_status")
    assert status["success"] is True and status["data"]["authorized"] is False


def test_screen_capture_and_monitors(reset_safety_gate):
    """Valida a enumeração de monitores e a captura real de tela quando autorizado."""
    safety_gate.authorize()
    try:
        monitors = get_monitors_info()
        assert len(monitors) >= 1 and monitors[0]["width"] > 0
        res_full = capture_screen(format="jpeg")
        assert res_full["width"] > 0 and len(res_full["imageBase64"]) > 100
        assert res_full["format"] == "jpeg" and res_full["dpiScale"] > 0

        region = {"x": 0, "y": 0, "width": 100, "height": 100}
        res_reg = capture_screen(region=region, format="png")
        assert res_reg["width"] == 100 and res_reg["height"] == 100
    finally:
        safety_gate.revoke("Fim do teste de tela")


def test_mouse_and_keyboard_actions_when_authorized(reset_safety_gate):
    """Valida as operações de mouse e teclado quando a autorização está concedida."""
    safety_gate.authorize()
    try:
        pos = get_cursor_position()
        assert isinstance(pos[0], int) and isinstance(pos[1], int)
        assert scroll_mouse(delta_y=0)["scrolled"] is True
        res_type = type_text("áéíóú çãõ", delay_ms=5)
        assert res_type["success"] is True and res_type["typedChars"] == len("áéíóú çãõ")
        release_all_keys()
        release_mouse_buttons()
    finally:
        safety_gate.revoke("Fim do teste de automação")


def test_execute_computer_action_dispatcher(reset_safety_gate):
    """Testa o despachante universal com comandos válidos sob autorização."""
    safety_gate.authorize()
    try:
        st = execute_computer_action("computer_get_status")
        assert st["success"] is True and st["data"]["authorized"] is True
        cur = execute_computer_action("computer_get_cursor")
        assert cur["success"] is True and "x" in cur["data"]
        typ = execute_computer_action("computer_keyboard_type", {"text": "Teste", "delayMs": 5})
        assert typ["success"] is True and typ["data"]["typedChars"] == 5
        inv = execute_computer_action("computer_comando_invalido")
        assert inv["success"] is False and "desconhecida" in inv["error"]
    finally:
        safety_gate.revoke("Fim do teste do despachante")
