"""Módulo de Localização de Janelas e Coordenadas Win32 para Background Use.

Permite identificar o identificador (hwnd) sob coordenadas de tela e converter
coordenadas absolutas de monitor para a área cliente da janela correspondente.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

user32 = ctypes.windll.user32
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetDesktopWindow.restype = wintypes.HWND

DESKTOP_ACCESS = 0x01FF  # Leitura e escrita no desktop interativo ativo


def ensure_thread_desktop() -> bool:
    """Anexa a thread atual ao desktop de entrada interativo ativo."""
    try:
        hdesk = user32.OpenInputDesktop(0, False, DESKTOP_ACCESS)
        if hdesk:
            return bool(user32.SetThreadDesktop(hdesk))
    except Exception:
        pass
    return False


def find_window_at(x: int, y: int) -> int:
    """Identifica o handle da janela (hwnd) sob as coordenadas absolutas (x, y)."""
    ensure_thread_desktop()
    pt = wintypes.POINT(int(x), int(y))
    hwnd = user32.WindowFromPoint(pt)
    if hwnd and user32.IsWindow(hwnd):
        return int(hwnd)
    return int(user32.GetDesktopWindow())


def screen_to_client(hwnd: int, x: int, y: int) -> Tuple[int, int]:
    """Converte coordenadas absolutas de tela para coordenadas da janela cliente."""
    if not hwnd or not user32.IsWindow(wintypes.HWND(hwnd)):
        return int(x), int(y)
    pt = wintypes.POINT(int(x), int(y))
    if user32.ScreenToClient(wintypes.HWND(hwnd), ctypes.byref(pt)):
        return int(pt.x), int(pt.y)
    return int(x), int(y)


def resolve_target_window(
    x: int, y: int, hwnd: Optional[int] = None
) -> Tuple[int, int, int]:
    """Resolve o handle da janela alvo e as coordenadas clientes relativas."""
    if hwnd and user32.IsWindow(wintypes.HWND(hwnd)):
        target_hwnd = int(hwnd)
    else:
        target_hwnd = find_window_at(x, y)
    cx, cy = screen_to_client(target_hwnd, x, y)
    return target_hwnd, cx, cy
