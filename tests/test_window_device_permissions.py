"""Testes unitários para permissões granulares de mouse e teclado por janela e nome do túnel.

Verifica se a desativação de mouse ou teclado na atribuição de janelas bloqueia
ações físicas no background com DEVICE_DISABLED, e testa a persistência do nome amigável do túnel.
"""

from __future__ import annotations
import importlib
import pytest
from src.computer import execute_computer_action
from src.computer.mouse_background import post_mouse_click, post_mouse_move
from src.computer.keyboard_background import post_keyboard_type, post_key_press
from src.computer.safety_gate import safety_gate
from src.core.tunnel_config import (
    save_tunnel_name,
    get_tunnel_name,
    get_tunnel_display_label,
    get_tunnel_id,
    save_tunnel_id
)

wa_mod = importlib.import_module("src.computer.window_assignments")
window_assignments = wa_mod.window_assignments


@pytest.fixture(autouse=True)
def clean_assignments_and_mocks(monkeypatch):
    """Limpa atribuições e simula funções Win32 para isolamento."""
    window_assignments.clear()
    monkeypatch.setattr(wa_mod.user32, "IsWindow", lambda _hwnd: 1)
    monkeypatch.setattr(wa_mod, "window_identity", lambda _hwnd: (100, 200))
    monkeypatch.setattr(wa_mod, "window_root", lambda hwnd: int(hwnd))
    yield
    window_assignments.clear()
    safety_gate.revoke("fim do teste")


def test_assignment_device_flags_default():
    """Garante que por padrão tanto mouse quanto teclado sejam permitidos."""
    item = window_assignments.assign("sess-1", 42)
    assert item.allow_mouse is True
    assert item.allow_keyboard is True
    assert window_assignments.can_mouse("sess-1") is True
    assert window_assignments.can_keyboard("sess-1") is True


def test_assignment_device_flags_custom():
    """Valida gravação e consulta quando mouse é desmarcado e teclado é mantido."""
    item = window_assignments.assign("sess-2", 42, allow_mouse=False, allow_keyboard=True)
    assert item.allow_mouse is False
    assert item.allow_keyboard is True
    assert window_assignments.can_mouse("sess-2") is False
    assert window_assignments.can_keyboard("sess-2") is True


def test_mouse_blocked_when_allow_mouse_is_false():
    """Verifica que post_mouse_click e post_mouse_move falham com DEVICE_DISABLED se desativados."""
    safety_gate.authorize()
    window_assignments.assign("sess-no-mouse", 42, allow_mouse=False, allow_keyboard=True)

    with pytest.raises(ValueError, match="DEVICE_DISABLED.*mouse"):
        post_mouse_click("left", x=10, y=10, session_id="sess-no-mouse")

    with pytest.raises(ValueError, match="DEVICE_DISABLED.*mouse"):
        post_mouse_move(20, 20, session_id="sess-no-mouse")

    # Também valida via despachante público
    res = execute_computer_action("computer_mouse_click", {
        "button": "left", "x": 10, "y": 10, "background": True, "session_id": "sess-no-mouse"
    })
    assert res["success"] is False
    assert "DEVICE_DISABLED" in res["error"]


def test_keyboard_blocked_when_allow_keyboard_is_false():
    """Verifica que post_keyboard_type e post_key_press falham com DEVICE_DISABLED se desativados."""
    safety_gate.authorize()
    window_assignments.assign("sess-no-kbd", 42, allow_mouse=True, allow_keyboard=False)

    with pytest.raises(ValueError, match="DEVICE_DISABLED.*teclado"):
        post_keyboard_type("olá mundo", session_id="sess-no-kbd")

    with pytest.raises(ValueError, match="DEVICE_DISABLED.*teclado"):
        post_key_press("enter", session_id="sess-no-kbd")

    # Também valida via despachante público
    res = execute_computer_action("computer_keyboard_type", {
        "text": "olá mundo", "background": True, "session_id": "sess-no-kbd"
    })
    assert res["success"] is False
    assert "DEVICE_DISABLED" in res["error"]


def test_tunnel_name_save_and_display():
    """Testa salvar e recuperar o nome amigável do túnel para facilitar identificação."""
    original_name = get_tunnel_name()
    original_id = get_tunnel_id()
    try:
        saved = save_tunnel_name("MeuAgenteEspecial")
        assert saved == "MeuAgenteEspecial"
        assert get_tunnel_name() == "MeuAgenteEspecial"

        fake_id = "tunnel_" + "a" * 32
        save_tunnel_id(fake_id)
        label = get_tunnel_display_label()
        assert "MeuAgenteEspecial" in label
        assert fake_id[:11] in label
    finally:
        save_tunnel_name(original_name)
        if original_id:
            save_tunnel_id(original_id)
