"""Módulo de Controle Virtual de Mouse em Segundo Plano (Background Win32).
Despacha mensagens Win32 via PostMessageW diretamente para a janela alvo,
mantendo o cursor virtual isolado sem alterar o ponteiro físico.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import threading
import time
from typing import Any, Dict, Optional, Tuple
from .safety_gate import safety_gate
from .window_finder import resolve_target_window

user32 = ctypes.windll.user32
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK = 0x0200, 0x0201, 0x0202, 0x0203
WM_RBUTTONDOWN, WM_RBUTTONUP, WM_MBUTTONDOWN, WM_MBUTTONUP = 0x0204, 0x0205, 0x0207, 0x0208
WM_MOUSEWHEEL, WM_MOUSEHWHEEL, MK_LBUTTON, MK_RBUTTON, MK_MBUTTON = 0x020A, 0x020E, 0x0001, 0x0002, 0x0010

_cursor_lock = threading.Lock()
_agent_cursor: Dict[str, int] = {"x": 0, "y": 0, "last_hwnd": 0}


def _makelparam(x: int, y: int) -> int:
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


def _set_cursor(x: int, y: int, hwnd: int) -> None:
    with _cursor_lock:
        _agent_cursor["x"], _agent_cursor["y"], _agent_cursor["last_hwnd"] = int(x), int(y), hwnd


def get_agent_cursor_position() -> Tuple[int, int]:
    """Retorna as coordenadas virtuais (x, y) do cursor exclusivo do agente."""
    with _cursor_lock:
        return _agent_cursor["x"], _agent_cursor["y"]


def post_mouse_move(x: int, y: int, hwnd: Optional[int] = None) -> Dict[str, Any]:
    """Despacha movimento de mouse em segundo plano para a janela alvo."""
    safety_gate.check_authorization("move_mouse")
    target_hwnd, cx, cy = resolve_target_window(x, y, hwnd)
    _set_cursor(x, y, target_hwnd)
    user32.PostMessageW(wintypes.HWND(target_hwnd), WM_MOUSEMOVE, 0, _makelparam(cx, cy))
    return {"currentX": int(x), "currentY": int(y), "background": True, "targetHwnd": target_hwnd}


def post_mouse_click(
    button: str = "left", double: bool = False,
    x: Optional[int] = None, y: Optional[int] = None, hwnd: Optional[int] = None
) -> Dict[str, Any]:
    """Despacha clique simples ou duplo em background para a janela alvo."""
    safety_gate.check_authorization("click_mouse")
    with _cursor_lock:
        tx, ty = (_agent_cursor["x"] if x is None else int(x)), (_agent_cursor["y"] if y is None else int(y))
    target_hwnd, cx, cy = resolve_target_window(tx, ty, hwnd)
    _set_cursor(tx, ty, target_hwnd)
    lp, btn = _makelparam(cx, cy), button.lower()
    down_msg, up_msg, mk = {
        "right": (WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON),
        "middle": (WM_MBUTTONDOWN, WM_MBUTTONUP, MK_MBUTTON)
    }.get(btn, (WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON))
    hw = wintypes.HWND(target_hwnd)
    if double and btn == "left":
        user32.PostMessageW(hw, WM_LBUTTONDBLCLK, mk, lp)
    else:
        user32.PostMessageW(hw, down_msg, mk, lp)
        time.sleep(0.02)
    user32.PostMessageW(hw, up_msg, 0, lp)
    return {"clicked": True, "button": button, "double": double, "background": True, "position": {"x": tx, "y": ty}}


def post_mouse_drag(
    start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 10, hwnd: Optional[int] = None
) -> Dict[str, Any]:
    """Arrasta suavemente o cursor virtual de início ao fim em segundo plano."""
    safety_gate.check_authorization("drag_mouse")
    target_hwnd, sx, sy = resolve_target_window(start_x, start_y, hwnd)
    hw, n_steps = wintypes.HWND(target_hwnd), max(int(steps), 2)
    user32.PostMessageW(hw, WM_MOUSEMOVE, 0, _makelparam(sx, sy))
    user32.PostMessageW(hw, WM_LBUTTONDOWN, MK_LBUTTON, _makelparam(sx, sy))
    for i in range(1, n_steps + 1):
        ix = int(start_x + (end_x - start_x) * (i / n_steps))
        iy = int(start_y + (end_y - start_y) * (i / n_steps))
        _, icx, icy = resolve_target_window(ix, iy, target_hwnd)
        user32.PostMessageW(hw, WM_MOUSEMOVE, MK_LBUTTON, _makelparam(icx, icy))
        time.sleep(0.01)
    _, ex, ey = resolve_target_window(end_x, end_y, target_hwnd)
    user32.PostMessageW(hw, WM_LBUTTONUP, 0, _makelparam(ex, ey))
    _set_cursor(end_x, end_y, target_hwnd)
    return {"dragged": True, "from": {"x": start_x, "y": start_y}, "to": {"x": end_x, "y": end_y}, "background": True}


def post_mouse_scroll(
    delta_y: int = 0, delta_x: int = 0, x: Optional[int] = None, y: Optional[int] = None, hwnd: Optional[int] = None
) -> Dict[str, Any]:
    """Emite rotação na roda do mouse via mensagem Win32 em background."""
    safety_gate.check_authorization("scroll_mouse")
    with _cursor_lock:
        tx, ty = (_agent_cursor["x"] if x is None else int(x)), (_agent_cursor["y"] if y is None else int(y))
    target_hwnd, _, _ = resolve_target_window(tx, ty, hwnd)
    hw, lp = wintypes.HWND(target_hwnd), _makelparam(tx, ty)
    if delta_y != 0:
        user32.PostMessageW(hw, WM_MOUSEWHEEL, (int(delta_y) << 16) & 0xFFFFFFFF, lp)
    if delta_x != 0:
        user32.PostMessageW(hw, WM_MOUSEHWHEEL, (int(delta_x) << 16) & 0xFFFFFFFF, lp)
    return {"scrolled": True, "deltaY": delta_y, "deltaX": delta_x, "background": True}
