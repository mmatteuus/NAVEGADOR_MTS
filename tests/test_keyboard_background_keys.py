"""Testes de validação anterior à resolução do alvo virtual."""

from unittest.mock import Mock

import pytest

from src.computer import keyboard_background as keyboard
from src.computer import safety_gate


@pytest.fixture(autouse=True)
def authorize() -> None:
    safety_gate.authorize()
    yield
    safety_gate.revoke("Fim do teste de validação de teclas")


def test_invalid_key_does_not_resolve_or_pin_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tecla Unicode não é convertida silenciosamente em VK."""
    resolver = Mock(side_effect=AssertionError("alvo não deveria ser resolvido"))
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", resolver)
    with pytest.raises(ValueError, match="Tecla desconhecida"):
        keyboard.post_key_press("😀", hwnd=321)
    resolver.assert_not_called()


def test_unknown_modifier_is_rejected_before_target_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Modificador fora de Ctrl/Alt/Shift/Win não altera o alvo."""
    resolver = Mock(side_effect=AssertionError("alvo não deveria ser resolvido"))
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", resolver)
    with pytest.raises(ValueError, match="Tecla desconhecida"):
        keyboard.post_key_press("a", modifiers=["tab"], hwnd=321)
    resolver.assert_not_called()


def test_meta_modifier_uses_windows_virtual_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """O alias Meta mantém o mesmo VK do modificador Win físico."""
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 321)
    monkeypatch.setattr(keyboard, "keyboard_target_identity", lambda _hwnd: (1, 1))
    monkeypatch.setattr(keyboard, "revalidate_keyboard_target", lambda _hwnd, _identity: None)
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda _h, msg, wp, _lp: calls.append((msg, wp)) or 1)
    keyboard.post_key_press("a", modifiers=["meta"], hwnd=321)
    assert calls[0] == (keyboard.WM_KEYDOWN, keyboard.VK_MAP["win"])
