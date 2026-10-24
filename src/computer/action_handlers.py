import os
from typing import Any, Dict

from .mouse import (
    click_mouse, drag_mouse, move_mouse, scroll_mouse,
)
from .keyboard import press_key, type_text
from .screen import capture_screen
from .mouse_background import (
    post_mouse_click, post_mouse_drag,
    post_mouse_move, post_mouse_scroll,
)
from .keyboard_background import post_key_press, post_keyboard_type


def _handle_screenshot(params: Dict[str, Any], bg: bool, hwnd: Any, sid: Any) -> Any:
    return capture_screen(
        monitor_index=params.get("monitorIndex"),
        region=params.get("region"), format=params.get("format", "png")
    )


def _handle_mouse_move(params: Dict[str, Any], bg: bool, hwnd: Any, sid: Any) -> Any:
    if bg:
        return post_mouse_move(int(params["x"]), int(params["y"]), hwnd=hwnd, session_id=sid)
    return move_mouse(
        int(params["x"]), int(params["y"]),
        smooth=params.get("smooth", True), duration_ms=int(params.get("durationMs", 200))
    )


def _handle_mouse_click(params: Dict[str, Any], bg: bool, hwnd: Any, sid: Any) -> Any:
    btn, dbl = params.get("button", "left"), bool(params.get("double", False))
    if bg:
        return post_mouse_click(
            button=btn, double=dbl, x=params.get("x"), y=params.get("y"), hwnd=hwnd, session_id=sid
        )
    return click_mouse(button=btn, double=dbl, hold_ms=int(params.get("holdMs", 50)))


def _handle_mouse_drag(params: Dict[str, Any], bg: bool, hwnd: Any, sid: Any) -> Any:
    sx, sy, ex, ey = int(params["startX"]), int(params["startY"]), int(params["endX"]), int(params["endY"])
    if bg:
        return post_mouse_drag(
            sx, sy, ex, ey, steps=int(params.get("steps", 10)), hwnd=hwnd, session_id=sid
        )
    return drag_mouse(sx, sy, ex, ey, steps=int(params.get("steps", 25)))


def _handle_mouse_scroll(params: Dict[str, Any], bg: bool, hwnd: Any, sid: Any) -> Any:
    dy = int(params.get("deltaY", params.get("delta", 0)))
    dx = int(params.get("deltaX", 0))
    if bg:
        return post_mouse_scroll(
            dy, dx, x=params.get("x"), y=params.get("y"), hwnd=hwnd, session_id=sid
        )
    return scroll_mouse(delta_y=dy, delta_x=dx)


def _handle_keyboard_type(params: Dict[str, Any], bg: bool, hwnd: Any, sid: Any) -> Any:
    txt, dly = str(params["text"]), int(params.get("delayMs", 5))
    if bg:
        return post_keyboard_type(txt, delay_ms=dly, hwnd=hwnd)
    return type_text(txt, delay_ms=dly)


def _handle_key_press(params: Dict[str, Any], bg: bool, hwnd: Any, sid: Any) -> Any:
    k, mods = str(params["key"]), params.get("modifiers")
    if bg:
        return post_key_press(k, modifiers=mods, hwnd=hwnd)
    return press_key(k, modifiers=mods)


def _handle_launch_app(params: Dict[str, Any], bg: bool, hwnd: Any, sid: Any) -> Any:
    target = str(params.get("app", params.get("path", "excel")))
    os.startfile(target)
    return {"launched": target}


_ACTION_HANDLERS = {
    "screenshot": _handle_screenshot,
    "screen": _handle_screenshot,
    "mouse_move": _handle_mouse_move,
    "move": _handle_mouse_move,
    "mouse_click": _handle_mouse_click,
    "click": _handle_mouse_click,
    "mouse_drag": _handle_mouse_drag,
    "drag": _handle_mouse_drag,
    "mouse_scroll": _handle_mouse_scroll,
    "scroll": _handle_mouse_scroll,
    "keyboard_type": _handle_keyboard_type,
    "type": _handle_keyboard_type,
    "key_press": _handle_key_press,
    "press_key": _handle_key_press,
    "key": _handle_key_press,
    "launch_app": _handle_launch_app,
    "open_app": _handle_launch_app,
    "launch": _handle_launch_app,
}
