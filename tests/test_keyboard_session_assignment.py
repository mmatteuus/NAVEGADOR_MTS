"""Regressões para isolamento do teclado virtual por sessão MCP."""

from __future__ import annotations

import ctypes
from types import SimpleNamespace

from src.computer import keyboard_background as keyboard
from src.computer import keyboard_target as target
from src.computer.safety_gate import safety_gate
from src.mcp.computer_dispatch import _plan


def test_keyboard_targets_are_independent_per_session(monkeypatch):
    """Duas sessões não podem reutilizar o HWND fixado pela outra."""
    safety_gate.authorize()
    identities = {101: (1, 11), 202: (2, 22)}
    monkeypatch.setattr(target.user32, "IsWindow", lambda _hwnd: 1)

    def pid(hwnd, out):
        tid, process = identities[int(hwnd.value)]
        ctypes.cast(out, ctypes.POINTER(target.wintypes.DWORD)).contents.value = process
        return tid

    monkeypatch.setattr(target.user32, "GetWindowThreadProcessId", pid)
    monkeypatch.setattr(target, "is_target_in_use", lambda _hwnd: False)
    target.clear_keyboard_target()
    assert target.resolve_keyboard_target(101, session_id="a") == 101
    assert target.resolve_keyboard_target(202, session_id="b") == 202
    assert target.resolve_keyboard_target(session_id="a") == 101
    assert target.resolve_keyboard_target(session_id="b") == 202
    target.clear_keyboard_target()
    safety_gate.revoke("fim")


def test_keyboard_message_carries_session_target(monkeypatch):
    """A fila de uma sessão envia mensagens apenas ao HWND atribuído a ela."""
    safety_gate.authorize()
    target.clear_keyboard_target()
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda hwnd=None, session_id=None: 700 if session_id == "a" else 800)
    monkeypatch.setattr(keyboard, "keyboard_target_identity", lambda _hwnd: (1, 1))
    monkeypatch.setattr(keyboard, "revalidate_keyboard_target", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(keyboard.window_assignments, "get", lambda sid: SimpleNamespace(hwnd=700 if sid == "a" else 800))
    monkeypatch.setattr(keyboard.window_assignments, "validate", lambda _lease: 1)
    sent = []
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda hwnd, msg, wp, lp: sent.append((int(hwnd.value), msg, wp)) or 1)
    keyboard.post_keyboard_type("x", delay_ms=0, session_id="a")
    keyboard.post_keyboard_type("y", delay_ms=0, session_id="b")
    assert [row[0] for row in sent] == [700, 800]
    target.clear_keyboard_target()
    safety_gate.revoke("fim")


def test_computer_plan_preserves_transport_session():
    """O dispatcher não pode perder a identidade confiável do transporte."""
    operation, params = _plan("computer_keyboard_action", {
        "action": "type", "text": "ok", "sessionId": "agent-a"
    })[0]
    assert operation == "computer_keyboard_type"
    assert params["sessionId"] == "agent-a"
