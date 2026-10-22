"""Testes unitários do canal de teclado virtual, sem digitação no desktop."""

from __future__ import annotations

import ctypes
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from src.computer import keyboard_background as keyboard
from src.computer import keyboard_target as target
from src.computer.safety_gate import SecurityGateError, safety_gate


@pytest.fixture(autouse=True)
def authorized_keyboard(monkeypatch: pytest.MonkeyPatch) -> None:
    safety_gate.authorize()
    target.clear_keyboard_target()
    monkeypatch.setattr(keyboard, "keyboard_target_identity", lambda _hwnd: (1, 1))
    monkeypatch.setattr(keyboard, "revalidate_keyboard_target", lambda _hwnd, _identity: None)
    yield
    target.clear_keyboard_target()
    safety_gate.revoke("Fim dos testes de teclado virtual")


def test_explicit_invalid_target_fails_without_cursor_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Um hwnd explícito inválido não pode redirecionar para outra janela."""
    monkeypatch.setattr(target.user32, "IsWindow", lambda _hwnd: 0)
    fallback = Mock(side_effect=AssertionError("fallback indevido"))
    monkeypatch.setattr(target, "find_window_at", fallback)

    with pytest.raises(ValueError, match="TARGET_INVALID"):
        target.resolve_keyboard_target(123)
    fallback.assert_not_called()


def test_focused_target_is_rejected_without_changing_focus(monkeypatch: pytest.MonkeyPatch) -> None:
    """O canal virtual recusa um controle que o usuário está usando."""
    monkeypatch.setattr(target.user32, "IsWindow", lambda _hwnd: 1)
    def window_pid(_hwnd, pid):
        ctypes.cast(pid, ctypes.POINTER(target.wintypes.DWORD)).contents.value = 7
        return 1
    monkeypatch.setattr(target.user32, "GetWindowThreadProcessId", window_pid)
    monkeypatch.setattr(target, "is_target_in_use", lambda _hwnd: True)
    with pytest.raises(ValueError, match="TARGET_IN_USE"):
        target.resolve_keyboard_target(123)


def test_keyboard_target_is_pinned_after_first_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Um hwnd explícito permanece fixado mesmo se o cursor virtual mudar."""
    monkeypatch.setattr(target.user32, "IsWindow", lambda _hwnd: 1)
    def window_pid(_hwnd, pid):
        ctypes.cast(pid, ctypes.POINTER(target.wintypes.DWORD)).contents.value = 7
        return 1
    monkeypatch.setattr(target.user32, "GetWindowThreadProcessId", window_pid)
    assert target.resolve_keyboard_target(321) == 321
    monkeypatch.setattr(target, "find_window_at", lambda _x, _y: 654)
    assert target.resolve_keyboard_target() == 321


def test_explicit_target_identity_reuse_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Um HWND reutilizado por outro PID/thread não recebe mensagens."""
    identity = [(1, 7), (2, 8)]
    monkeypatch.setattr(target.user32, "IsWindow", lambda _hwnd: 1)
    def window_pid(_hwnd, pid):
        tid, process = identity[0]
        ctypes.cast(pid, ctypes.POINTER(target.wintypes.DWORD)).contents.value = process
        return tid
    monkeypatch.setattr(target.user32, "GetWindowThreadProcessId", window_pid)
    assert target.resolve_keyboard_target(321) == 321
    identity[0] = identity[1]
    with pytest.raises(ValueError, match="TARGET_INVALID"):
        target.resolve_keyboard_target()


def test_unicode_posts_utf16_units_and_rechecks_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    """Caracteres fora do BMP viram dois WM_CHAR e a autorização é revalidada."""
    posted: list[tuple[int, int]] = []
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 321)
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda _h, msg, wp, _lp: posted.append((msg, wp)) or 1)
    result = keyboard.post_keyboard_type("A😀", delay_ms=0, hwnd=321)
    assert result["typedChars"] == 2
    assert [value for _, value in posted] == [ord("A"), 0xD83D, 0xDE00]


def test_keydown_failure_releases_already_posted_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha no segundo keydown sempre libera o modificador já pressionado."""
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 321)
    def post(_h, msg, wp, _lp):
        calls.append((msg, wp))
        return len(calls) != 2
    monkeypatch.setattr(keyboard.user32, "PostMessageW", post)

    with pytest.raises(RuntimeError, match="KEYBOARD_POST_FAILED"):
        keyboard.post_key_press("c", modifiers=["ctrl"], hwnd=321)
    assert calls == [(keyboard.WM_KEYDOWN, keyboard.VK_MAP["ctrl"]),
                     (keyboard.WM_KEYDOWN, keyboard.VK_MAP["c"]),
                     (keyboard.WM_KEYUP, keyboard.VK_MAP["ctrl"])]


def test_keyup_failure_is_reported_after_all_releases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha de soltura não é silenciosa e ainda tenta todas as teclas."""
    calls: list[int] = []
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 321)
    def post(_h, msg, wp, _lp):
        calls.append(msg)
        return msg != keyboard.WM_KEYUP
    monkeypatch.setattr(keyboard.user32, "PostMessageW", post)
    with pytest.raises(RuntimeError, match="KEYBOARD_RELEASE_FAILED"):
        keyboard.post_key_press("a", modifiers=["ctrl"], hwnd=321)
    assert calls.count(keyboard.WM_KEYUP) == 2


def test_revocation_mid_text_stops_before_next_post(monkeypatch: pytest.MonkeyPatch) -> None:
    """Revogação entre lotes interrompe a fila sem enviar o próximo caractere."""
    posted: list[int] = []
    checks = iter([None, "raise"])
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 321)
    def check(_name):
        if next(checks) == "raise":
            raise SecurityGateError("revogado")
    monkeypatch.setattr(keyboard.safety_gate, "check_authorization", check)
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda _h, _m, wp, _lp: posted.append(wp) or 1)
    with pytest.raises(SecurityGateError):
        keyboard.post_keyboard_type("ab", delay_ms=0, hwnd=321)
    assert posted == []


def test_concurrent_keypresses_are_serialized(monkeypatch: pytest.MonkeyPatch) -> None:
    """Duas chamadas concorrentes não intercalam seus pares de tecla."""
    posted: list[tuple[int, int]] = []
    monkeypatch.setattr(keyboard, "resolve_keyboard_target", lambda _hwnd=None: 321)
    monkeypatch.setattr(keyboard.user32, "PostMessageW", lambda _h, msg, wp, _lp: posted.append((msg, wp)) or 1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda key: keyboard.post_key_press(key, hwnd=321), ["a", "b"]))
    assert posted in ([
        (keyboard.WM_KEYDOWN, keyboard.VK_MAP["a"]), (keyboard.WM_KEYUP, keyboard.VK_MAP["a"]),
        (keyboard.WM_KEYDOWN, keyboard.VK_MAP["b"]), (keyboard.WM_KEYUP, keyboard.VK_MAP["b"])
    ], [
        (keyboard.WM_KEYDOWN, keyboard.VK_MAP["b"]), (keyboard.WM_KEYUP, keyboard.VK_MAP["b"]),
        (keyboard.WM_KEYDOWN, keyboard.VK_MAP["a"]), (keyboard.WM_KEYUP, keyboard.VK_MAP["a"])
    ])
