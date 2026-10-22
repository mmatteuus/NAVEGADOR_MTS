"""QA independente do contrato de teclado virtual do agente.

Os testes usam apenas mensagens Win32 mockadas; nenhuma janela ou entrada física
é acionada. A entrega em um controle real continua sendo uma validação separada.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.computer import post_key_press, safety_gate
from src.computer import keyboard_background as keyboard


def test_background_keyboard_source_has_no_focus_or_physical_input_api() -> None:
    """Impede regressão para APIs que roubam foco ou teclado físico."""
    source = Path(keyboard.__file__).read_text(encoding="utf-8")
    for forbidden in ("SendInput", "SetFocus", "SetForegroundWindow", "keybd_event"):
        assert forbidden not in source, f"API física/foco proibida encontrada: {forbidden}"


def test_unknown_modifier_is_rejected_before_posting(
    reset_safety_gate: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Modificador desconhecido não pode ser silenciosamente descartado."""
    safety_gate.authorize()
    calls = []
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 123)
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda *args: calls.append(args) or 1)
    try:
        with pytest.raises(ValueError, match="Tecla desconhecida"):
            post_key_press("A", modifiers=["modifier_inexistente"], hwnd=123)
        assert calls == [], "modificador inválido não pode emitir keydown/keyup"
    finally:
        safety_gate.revoke("fim do teste QA")


def test_key_messages_are_ordered_and_post_failure_is_reported(
    reset_safety_gate: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valida ordem keydown/keyup e falha explícita de PostMessageW."""
    safety_gate.authorize()
    events: list[tuple[int, int]] = []
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 123)
    monkeypatch.setattr(keyboard, "revalidate_keyboard_target", lambda *_args: None)
    monkeypatch.setattr(
        keyboard.user32,
        "PostMessageW",
        lambda _hwnd, message, key, _flags: events.append((message, key)) or 1,
    )
    try:
        result = post_key_press("A", modifiers=["shift"], hwnd=123)
        assert result["background"] is True
        assert [key for _message, key in events] == [0x10, 0x41, 0x41, 0x10]
        assert events[0][0] == keyboard.WM_KEYDOWN
        assert events[-1][0] == keyboard.WM_KEYUP

        events.clear()
        monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda *_args: 0)
        with pytest.raises(RuntimeError, match="KEYBOARD_POST_FAILED"):
            post_key_press("A", hwnd=123)
    finally:
        safety_gate.revoke("fim do teste QA")


def test_revocation_between_text_batches_stops_before_next_character(
    reset_safety_gate: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Revogação entre caracteres não deve emitir o lote seguinte."""
    safety_gate.authorize()
    posted: list[int] = []
    checks = iter([None, None, "revogado"])
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 123)
    monkeypatch.setattr(keyboard, "keyboard_target_identity", lambda _hwnd: (1, 1))
    monkeypatch.setattr(keyboard, "revalidate_keyboard_target", lambda *_args: None)
    monkeypatch.setattr(
        keyboard.safety_gate,
        "check_authorization",
        lambda _name: (_ for _ in ()).throw(RuntimeError("revogado"))
        if next(checks) == "revogado" else None,
    )
    monkeypatch.setattr(
        keyboard.user32,
        "PostMessageW",
        lambda _hwnd, _message, unit, _flags: posted.append(unit) or 1,
    )
    try:
        with pytest.raises(RuntimeError, match="revogado"):
            keyboard.post_keyboard_type("ab", delay_ms=0, hwnd=123)
        assert posted == [ord("a")]
    finally:
        safety_gate.revoke("fim do teste QA")
