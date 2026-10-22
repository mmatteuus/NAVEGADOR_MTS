"""Estado seguro do alvo virtual de teclado do agente."""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Optional

from .mouse_background import get_agent_cursor_position
from .window_finder import find_window_at

user32 = ctypes.windll.user32
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetForegroundWindow.restype = wintypes.HWND


class _GUIThreadInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
                ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
                ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
                ("rcCaret", wintypes.RECT)]


user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(_GUIThreadInfo)]
user32.GetGUIThreadInfo.restype = wintypes.BOOL

_lock = threading.RLock()
_target_hwnd = 0
_target_identity: tuple[int, int] | None = None


def is_valid_target(hwnd: Optional[int]) -> bool:
    """Confere existência da janela e que seu thread/processo ainda é válido."""
    if not hwnd:
        return False
    pid = wintypes.DWORD()
    handle = wintypes.HWND(int(hwnd))
    return bool(user32.IsWindow(handle) and user32.GetWindowThreadProcessId(handle, ctypes.byref(pid)) and pid.value)


def _identity(hwnd: int) -> tuple[int, int]:
    """Retorna PID/thread atuais para detectar reuso de HWND."""
    pid = wintypes.DWORD()
    tid = int(user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(pid)))
    return tid, int(pid.value)


def keyboard_target_identity(hwnd: int) -> tuple[int, int]:
    """Retorna a identidade atual do alvo para uma operação serializada."""
    return _identity(hwnd)


def is_target_in_use(hwnd: int) -> bool:
    """Detecta foco real exatamente no alvo, sem alterar a janela do usuário."""
    if int(user32.GetForegroundWindow() or 0) == int(hwnd):
        return True
    info = _GUIThreadInfo(ctypes.sizeof(_GUIThreadInfo))
    return bool(user32.GetGUIThreadInfo(0, ctypes.byref(info)) and int(info.hwndFocus or 0) == int(hwnd))


def revalidate_keyboard_target(hwnd: int, identity: tuple[int, int]) -> None:
    """Revalida identidade e foco antes de cada lote enviado ao Windows."""
    if not is_valid_target(hwnd) or _identity(hwnd) != identity:
        raise ValueError("TARGET_INVALID: alvo mudou durante a operação")
    if is_target_in_use(hwnd):
        raise ValueError("TARGET_IN_USE: alvo virtual está focado pelo usuário")


def resolve_keyboard_target(hwnd: Optional[int] = None) -> int:
    """Retorna alvo explícito, alvo fixado ou janela sob cursor virtual, nessa ordem."""
    global _target_hwnd, _target_identity
    with _lock:
        if hwnd is not None:
            if not is_valid_target(hwnd):
                raise ValueError("TARGET_INVALID: hwnd explícito não é uma janela válida")
            if is_target_in_use(int(hwnd)):
                raise ValueError("TARGET_IN_USE: alvo virtual está focado pelo usuário")
            _target_hwnd = int(hwnd)
            _target_identity = _identity(_target_hwnd)
            return _target_hwnd
        if _target_hwnd and _target_identity is not None:
            if not is_valid_target(_target_hwnd) or _identity(_target_hwnd) != _target_identity:
                raise ValueError("TARGET_INVALID: alvo explícito foi encerrado ou reutilizado")
            if is_target_in_use(_target_hwnd):
                raise ValueError("TARGET_IN_USE: alvo virtual está focado pelo usuário")
            return _target_hwnd
        x, y = get_agent_cursor_position()
        candidate = find_window_at(x, y)
        if not is_valid_target(candidate):
            raise ValueError("TARGET_INVALID: nenhuma janela válida no cursor virtual")
        if is_target_in_use(int(candidate)):
            raise ValueError("TARGET_IN_USE: alvo virtual está focado pelo usuário")
        return int(candidate)


def clear_keyboard_target() -> None:
    """Limpa o alvo virtual, útil após encerramento ou revogação de sessão."""
    global _target_hwnd, _target_identity
    with _lock:
        _target_hwnd = 0
        _target_identity = None
