"""Regressões de lease, falha Win32 e paralelismo sem input físico."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
import pytest
from src.computer import keyboard_background as keyboard, mouse_background as mouse
from src.computer.safety_gate import safety_gate

@pytest.fixture(autouse=True)
def authorized():
    safety_gate.authorize(); yield; safety_gate.revoke("fim"); mouse.reset_agent_cursors()

def test_keyboard_uses_one_lease_for_all_characters(monkeypatch):
    lease = SimpleNamespace(hwnd=321); seen = []
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda *a, **k: 321)
    monkeypatch.setattr(keyboard, "keyboard_target_identity", lambda _: (1, 2))
    monkeypatch.setattr(keyboard.window_assignments, "get", lambda _: lease)
    monkeypatch.setattr(keyboard, "revalidate_keyboard_target", lambda *a, **k: seen.append(k["lease"]))
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda *a: 1)
    keyboard.post_keyboard_type("abc", delay_ms=0, session_id="agent")
    assert seen == [lease, lease, lease]

def test_mouse_revocation_between_dispatch_and_lease_fails(monkeypatch):
    monkeypatch.setattr(mouse, "resolve_target_window", lambda *a: (321, 1, 1))
    monkeypatch.setattr(mouse.window_assignments, "get", lambda _: None)
    with pytest.raises(ValueError, match="TARGET_REVOKED"):
        mouse.post_mouse_move(1, 1, hwnd=321, session_id="revoked")

def test_mouse_false_post_is_not_success(monkeypatch):
    lease = SimpleNamespace(hwnd=321)
    monkeypatch.setattr(mouse, "resolve_target_window", lambda *a: (321, 1, 1))
    monkeypatch.setattr(mouse.window_assignments, "get", lambda _: lease)
    monkeypatch.setattr(mouse.window_assignments, "validate", lambda _: 321)
    monkeypatch.setattr(mouse, "window_identity", lambda _: (1, 2))
    monkeypatch.setattr(mouse.user32, "PostMessageW", lambda *a: 0)
    with pytest.raises(RuntimeError, match="MOUSE_POST_FAILED"):
        mouse.post_mouse_click(hwnd=321, session_id="agent")

def test_keyboard_locks_are_per_session(monkeypatch):
    barrier = Barrier(2); leases = {"a": SimpleNamespace(hwnd=700), "b": SimpleNamespace(hwnd=800)}
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None, session_id=None: leases[session_id].hwnd)
    monkeypatch.setattr(keyboard, "keyboard_target_identity", lambda _: (1, 2))
    monkeypatch.setattr(keyboard.window_assignments, "get", lambda sid: leases[sid])
    monkeypatch.setattr(keyboard, "revalidate_keyboard_target", lambda *a, **k: None)
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda *a: barrier.wait(timeout=2) or 1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda sid: keyboard.post_keyboard_type("x", delay_ms=0, session_id=sid), ["a", "b"]))
    assert all(result["success"] for result in results)

def test_keyboard_skips_keyup_after_hwnd_reuse(monkeypatch):
    lease = SimpleNamespace(hwnd=321); sent = []; identities = [(1, 2), (9, 9)]
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda *a, **k: 321)
    monkeypatch.setattr(keyboard, "keyboard_target_identity", lambda _: identities.pop(0))
    monkeypatch.setattr(keyboard.window_assignments, "get", lambda _: lease)
    monkeypatch.setattr(keyboard, "revalidate_keyboard_target", lambda *a, **k: None)
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda hwnd, msg, wp, lp: sent.append(msg) or 1)
    with pytest.raises(RuntimeError, match="KEYBOARD_RELEASE_FAILED"):
        keyboard.post_key_press("a", session_id="agent")
    assert keyboard.WM_KEYUP not in sent

def test_mouse_click_does_not_release_reused_hwnd(monkeypatch):
    lease = SimpleNamespace(hwnd=321); sent = []; identities = [(1, 2), (9, 9)]
    monkeypatch.setattr(mouse, "resolve_target_window", lambda *a: (321, 1, 1))
    monkeypatch.setattr(mouse, "window_identity", lambda _: identities.pop(0))
    monkeypatch.setattr(mouse.window_assignments, "get", lambda _: lease)
    monkeypatch.setattr(mouse.window_assignments, "validate", lambda _: True)
    monkeypatch.setattr(mouse.user32, "PostMessageW", lambda hwnd, msg, wp, lp: sent.append(msg) or 1)
    with pytest.raises(RuntimeError, match="MOUSE_RELEASE_BLOCKED"):
        mouse.post_mouse_click(hwnd=321, session_id="agent")
    assert mouse.WM_LBUTTONUP not in sent
