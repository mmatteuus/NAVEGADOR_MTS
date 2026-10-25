"""Execução do arrasto virtual com lease e identidade fixos."""
from __future__ import annotations
import time

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON = 0x0200, 0x0201, 0x0202, 1

def run_drag(start_x, start_y, end_x, end_y, steps, target_hwnd, lease, identity,
             resolve_target, validate, post, safety, makelparam, set_cursor, session_id):
    sx, sy = resolve_target(start_x, start_y, target_hwnd)[1:]
    if not post(WM_MOUSEMOVE, 0, makelparam(sx, sy)):
        raise RuntimeError("MOUSE_POST_FAILED: movimento inicial não entrou na fila")
    if not post(WM_LBUTTONDOWN, MK_LBUTTON, makelparam(sx, sy)):
        raise RuntimeError("MOUSE_POST_FAILED: início do arrasto não entrou na fila")
    pressed, count = True, max(int(steps), 2)
    try:
        for index in range(1, count + 1):
            safety("drag_mouse")
            x = int(start_x + (end_x - start_x) * index / count)
            y = int(start_y + (end_y - start_y) * index / count)
            _, cx, cy = resolve_target(x, y, target_hwnd)
            validate(target_hwnd, lease, identity)
            if not post(WM_MOUSEMOVE, MK_LBUTTON, makelparam(cx, cy)):
                raise RuntimeError("MOUSE_POST_FAILED: movimento do arrasto não entrou na fila")
            time.sleep(0.01)
        _, cx, cy = resolve_target(end_x, end_y, target_hwnd)
        validate(target_hwnd, lease, identity)
        if not post(WM_LBUTTONUP, 0, makelparam(cx, cy)):
            raise RuntimeError("MOUSE_POST_FAILED: fim do arrasto não entrou na fila")
        pressed = False
    finally:
        if pressed:
            try:
                validate(target_hwnd, lease, identity)
                post(WM_LBUTTONUP, 0, makelparam(sx, sy))
            except ValueError:
                pass
    set_cursor(end_x, end_y, target_hwnd, session_id=session_id)
    return {"dragged": True, "from": {"x": start_x, "y": start_y},
            "to": {"x": end_x, "y": end_y}, "background": True}
