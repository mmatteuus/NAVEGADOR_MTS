from __future__ import annotations
import ctypes
from ctypes import wintypes
import threading, time
from typing import Any, Dict, Optional, Tuple
from .safety_gate import safety_gate
from .window_finder import resolve_target_window
from .window_assignments import window_assignments, window_identity
from .mouse_drag import run_drag

user32 = ctypes.windll.user32
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK = 0x0200, 0x0201, 0x0202, 0x0203
WM_RBUTTONDOWN, WM_RBUTTONUP, WM_MBUTTONDOWN, WM_MBUTTONUP = 0x0204, 0x0205, 0x0207, 0x0208
WM_MOUSEWHEEL, WM_MOUSEHWHEEL, MK_LBUTTON, MK_RBUTTON, MK_MBUTTON = 0x020A, 0x020E, 0x0001, 0x0002, 0x0010

_cursor_lock = threading.Lock()
_agent_cursors: Dict[str, Dict[str, int]] = {}


def _lease(session_id: Optional[str], hwnd: int):
    if not session_id or str(session_id).strip() == "":
        return None
    lease = window_assignments.get(session_id)
    if lease is None:
        raise ValueError("TARGET_REVOKED: sessão sem atribuição de janela")
    if not getattr(lease, "allow_mouse", True):
        raise ValueError("DEVICE_DISABLED: controle de mouse desativado pelo usuário para esta janela")
    if lease.hwnd != int(hwnd):
        raise ValueError("TARGET_REVOKED: atribuição ausente durante a ação")
    window_assignments.validate(lease)
    return lease


def _makelparam(x: int, y: int) -> int:
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


def _validate_target(hwnd: int, lease, identity) -> None:
    if window_identity(hwnd) != identity:
        raise ValueError("TARGET_INVALID: HWND foi reutilizado")
    if lease: window_assignments.validate(lease)


def _get_sid(session_id: Optional[str] = None) -> str:
    return str(session_id).strip() if session_id and str(session_id).strip() else "default"


def _set_cursor(x: int, y: int, hwnd: int, session_id: Optional[str] = None) -> None:
    sid = _get_sid(session_id)
    with _cursor_lock:
        _agent_cursors[sid] = {"x": int(x), "y": int(y), "last_hwnd": int(hwnd)}


def get_agent_cursor_position(session_id: Optional[str] = None) -> Tuple[int, int]:
    sid = _get_sid(session_id)
    with _cursor_lock:
        cur = _agent_cursors.get(sid)
        return (cur["x"], cur["y"]) if cur else (0, 0)


def post_mouse_move(x: int, y: int, hwnd: Optional[int] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    safety_gate.check_authorization("move_mouse")
    target_hwnd, cx, cy = resolve_target_window(x, y, hwnd)
    _lease(session_id, target_hwnd)
    _set_cursor(x, y, target_hwnd, session_id=session_id)
    if not user32.PostMessageW(wintypes.HWND(target_hwnd), WM_MOUSEMOVE, 0, _makelparam(cx, cy)):
        raise RuntimeError("MOUSE_POST_FAILED: WM_MOUSEMOVE não entrou na fila")
    return {"currentX": int(x), "currentY": int(y), "background": True, "targetHwnd": target_hwnd}


def post_mouse_click(
    button: str = "left", double: bool = False,
    x: Optional[int] = None, y: Optional[int] = None, hwnd: Optional[int] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    safety_gate.check_authorization("click_mouse")
    sid = _get_sid(session_id)
    with _cursor_lock:
        cur = _agent_cursors.get(sid, {"x": 0, "y": 0, "last_hwnd": 0})
        tx = cur["x"] if x is None else int(x)
        ty = cur["y"] if y is None else int(y)
    target_hwnd, cx, cy = resolve_target_window(tx, ty, hwnd)
    _lease(session_id, target_hwnd)
    original_identity = window_identity(target_hwnd)
    _set_cursor(tx, ty, target_hwnd, session_id=session_id)
    lp, btn = _makelparam(cx, cy), button.lower()
    down_msg, up_msg, mk = {
        "right": (WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON),
        "middle": (WM_MBUTTONDOWN, WM_MBUTTONUP, MK_MBUTTON)
    }.get(btn, (WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON))
    hw = wintypes.HWND(target_hwnd)
    if double and btn == "left":
        if not user32.PostMessageW(hw, WM_LBUTTONDBLCLK, mk, lp):
            raise RuntimeError("MOUSE_POST_FAILED: clique não entrou na fila")
    else:
        if not user32.PostMessageW(hw, down_msg, mk, lp):
            raise RuntimeError("MOUSE_POST_FAILED: botão não entrou na fila")
        time.sleep(0.02)
    if window_identity(target_hwnd) != original_identity:
        raise RuntimeError("MOUSE_RELEASE_BLOCKED: HWND foi reutilizado")
    if not user32.PostMessageW(hw, up_msg, 0, lp):
        raise RuntimeError("MOUSE_POST_FAILED: soltura não entrou na fila")
    return {"clicked": True, "button": button, "double": double, "background": True, "position": {"x": tx, "y": ty}}


def post_mouse_drag(
    start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 10,
    hwnd: Optional[int] = None, session_id: Optional[str] = None
) -> Dict[str, Any]:
    safety_gate.check_authorization("drag_mouse")
    target_hwnd, _, _ = resolve_target_window(start_x, start_y, hwnd)
    lease = _lease(session_id, target_hwnd)
    original_identity = window_identity(target_hwnd)
    return run_drag(start_x, start_y, end_x, end_y, steps, target_hwnd, lease, original_identity,
                    resolve_target_window, _validate_target,
                    lambda msg, wp, lp: user32.PostMessageW(wintypes.HWND(target_hwnd), msg, wp, lp),
                    safety_gate.check_authorization, _makelparam, _set_cursor, session_id)


def post_mouse_scroll(
    delta_y: int = 0, delta_x: int = 0, x: Optional[int] = None, y: Optional[int] = None,
    hwnd: Optional[int] = None, session_id: Optional[str] = None
) -> Dict[str, Any]:
    safety_gate.check_authorization("scroll_mouse")
    sid = _get_sid(session_id)
    with _cursor_lock:
        cur = _agent_cursors.get(sid, {"x": 0, "y": 0, "last_hwnd": 0})
        tx = cur["x"] if x is None else int(x)
        ty = cur["y"] if y is None else int(y)
    target_hwnd, _, _ = resolve_target_window(tx, ty, hwnd)
    _lease(session_id, target_hwnd)
    hw, lp = wintypes.HWND(target_hwnd), _makelparam(tx, ty)
    if delta_y != 0 and not user32.PostMessageW(hw, WM_MOUSEWHEEL, (int(delta_y) << 16) & 0xFFFFFFFF, lp):
        raise RuntimeError("MOUSE_POST_FAILED: roda vertical não entrou na fila")
    if delta_x != 0 and not user32.PostMessageW(hw, WM_MOUSEHWHEEL, (int(delta_x) << 16) & 0xFFFFFFFF, lp):
        raise RuntimeError("MOUSE_POST_FAILED: roda horizontal não entrou na fila")
    return {"scrolled": True, "deltaY": delta_y, "deltaX": delta_x, "background": True}


def reset_agent_cursors() -> None:
    with _cursor_lock:
        _agent_cursors.clear()
