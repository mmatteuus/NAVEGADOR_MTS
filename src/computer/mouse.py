"""
Módulo de Automação e Controle Seguro do Mouse no Windows.

Implementa movimentação suave por curvas Bézier, cliques humanos, arrasto,
rolagem e soltura compulsória via SendInput Win32, com tratamento para
múltiplos monitores (SM_XVIRTUALSCREEN) e detecção de intervenção física.
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import Tuple, Dict, Any
from .win32_types import (
    INPUT, INPUT_MOUSE, MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE,
    MOUSEEVENTF_VIRTUALDESK, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP, MOUSEEVENTF_MIDDLEDOWN,
    MOUSEEVENTF_MIDDLEUP, MOUSEEVENTF_WHEEL, MOUSEEVENTF_HWHEEL,
    SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN
)
from .safety_gate import safety_gate
from .kill_switch import kill_switch
from .mouse_bezier import generate_bezier_trajectory

user32 = ctypes.windll.user32
_physical_device_lock = threading.Lock()

def _get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    """Obtém as dimensões e offset da área de trabalho virtual multi-monitor."""
    vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = max(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN), 1)
    vh = max(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN), 1)
    return vx, vy, vw, vh

def _send_mouse_event(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> None:
    """Despacha uma estrutura INPUT de mouse diretamente para o subsistema Win32."""
    inp = INPUT(type=INPUT_MOUSE)
    inp.union.mi.dx = dx
    inp.union.mi.dy = dy
    inp.union.mi.mouseData = data
    inp.union.mi.dwFlags = flags
    inp.union.mi.time = 0
    inp.union.mi.dwExtraInfo = 0
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def get_cursor_position() -> Tuple[int, int]:
    """Retorna as coordenadas absolutas atuais (x, y) do ponteiro na tela."""
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)

def release_mouse_buttons() -> None:
    """Rotina de emergência para soltar todos os botões do mouse."""
    _send_mouse_event(MOUSEEVENTF_LEFTUP)
    _send_mouse_event(MOUSEEVENTF_RIGHTUP)
    _send_mouse_event(MOUSEEVENTF_MIDDLEUP)

kill_switch.register_cleanup_callback(release_mouse_buttons)

def _move_mouse_raw(x: int, y: int, smooth: bool = True, duration_ms: int = 200) -> Dict[str, Any]:
    cur_x, cur_y = get_cursor_position()
    if not smooth:
        user32.SetCursorPos(int(x), int(y))
        return {"currentX": x, "currentY": y}

    steps = max(int(duration_ms / 10), 10)
    caminho = generate_bezier_trajectory((cur_x, cur_y), (x, y), steps=steps)
    step_delay = (duration_ms / 1000.0) / len(caminho)

    last_emitted = (cur_x, cur_y)
    for px, py in caminho:
        real_x, real_y = get_cursor_position()
        if abs(real_x - last_emitted[0]) > 60 or abs(real_y - last_emitted[1]) > 60:
            return {"currentX": real_x, "currentY": real_y, "interrupted": True}
        user32.SetCursorPos(int(px), int(py))
        last_emitted = (int(px), int(py))
        time.sleep(step_delay)

    user32.SetCursorPos(int(x), int(y))
    return {"currentX": x, "currentY": y}

def move_mouse(x: int, y: int, smooth: bool = True, duration_ms: int = 200) -> Dict[str, Any]:
    """Move o ponteiro do mouse até (x, y) de forma suave ou instantânea."""
    safety_gate.check_authorization("move_mouse")
    with _physical_device_lock:
        return _move_mouse_raw(x, y, smooth=smooth, duration_ms=duration_ms)

def click_mouse(button: str = "left", double: bool = False, hold_ms: int = 50) -> Dict[str, Any]:
    """Executa um clique simples ou duplo na posição atual do mouse."""
    safety_gate.check_authorization("click_mouse")
    down_flag, up_flag = {
        "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
        "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
        "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP)
    }.get(button.lower(), (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP))

    vezes = 2 if double else 1
    with _physical_device_lock:
        for i in range(vezes):
            _send_mouse_event(down_flag)
            time.sleep(max(hold_ms / 1000.0, 0.02))
            _send_mouse_event(up_flag)
            if double and i == 0:
                time.sleep(0.08)
        pos_x, pos_y = get_cursor_position()
    return {"clicked": True, "button": button, "double": double, "position": {"x": pos_x, "y": pos_y}}

def drag_mouse(start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 25) -> Dict[str, Any]:
    """Clica e arrasta suavemente de (start_x, start_y) até (end_x, end_y)."""
    safety_gate.check_authorization("drag_mouse")
    with _physical_device_lock:
        _move_mouse_raw(start_x, start_y, smooth=False)
        time.sleep(0.05)
        _send_mouse_event(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.05)
        try:
            _move_mouse_raw(end_x, end_y, smooth=True, duration_ms=steps * 12)
        finally:
            _send_mouse_event(MOUSEEVENTF_LEFTUP)
    return {"dragged": True, "from": {"x": start_x, "y": start_y}, "to": {"x": end_x, "y": end_y}}

def scroll_mouse(delta_y: int = 0, delta_x: int = 0) -> Dict[str, Any]:
    """Emite rotação na roda do mouse (vertical e/ou horizontal)."""
    safety_gate.check_authorization("scroll_mouse")
    with _physical_device_lock:
        if delta_y != 0:
            _send_mouse_event(MOUSEEVENTF_WHEEL, data=int(delta_y))
        if delta_x != 0:
            _send_mouse_event(MOUSEEVENTF_HWHEEL, data=int(delta_x))
    return {"scrolled": True, "deltaY": delta_y, "deltaX": delta_x}
