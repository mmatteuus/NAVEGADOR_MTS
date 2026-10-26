"""Módulo de despacho e manipuladores para execute_computer_action."""

from __future__ import annotations
import os
from typing import Any, Dict, Callable
from .safety_gate import safety_gate
from .mouse import click_mouse, drag_mouse, get_cursor_position, move_mouse, scroll_mouse
from .keyboard import press_key, type_text
from .screen import capture_screen, get_monitors_info
from .mouse_background import (
    get_agent_cursor_position, post_mouse_click, post_mouse_drag,
    post_mouse_move, post_mouse_scroll,
)
from .keyboard_background import post_key_press, post_keyboard_type


def get_session_id(params: Dict[str, Any]) -> str | None:
    """Extrai o ID da sessão do contexto do MCP ou dos parâmetros."""
    try:
        from ..mcp.session_context import get_current_session_id
        ctx_sid = get_current_session_id()
    except Exception:
        ctx_sid = None
    return ctx_sid or params.get("session_id") or params.get("sessionId")


def handle_status(sid: str | None, params: Dict[str, Any]) -> Any:
    """Retorna o status de autorização e kill switch."""
    return {
        "authorized": safety_gate.is_authorized(),
        "killSwitchTriggered": safety_gate.is_kill_switch_triggered()
    }


def handle_cursor(sid: str | None, params: Dict[str, Any]) -> Any:
    """Retorna a posição atual do cursor e informações de monitores."""
    x, y = get_cursor_position()
    return {"x": x, "y": y, "monitors": get_monitors_info()}


def handle_agent_cursor(sid: str | None, params: Dict[str, Any]) -> Any:
    """Retorna a posição do cursor do agente virtual para a sessão."""
    ax, ay = get_agent_cursor_position(session_id=sid)
    return {"x": ax, "y": ay, "sessionId": sid or "default"}


def handle_window_action(sid: str | None, params: Dict[str, Any]) -> Any:
    """Executa ações UIA/janela."""
    from .window_action import execute
    return execute(sid, params)


def handle_screenshot(sid: str | None, bg: bool, hwnd: Any, params: Dict[str, Any]) -> Any:
    """Captura de tela física ou de janela em background."""
    if sid and bg:
        from .window_capture import capture
        return capture(sid, hwnd, params.get("format", "png"))
    return capture_screen(
        monitor_index=params.get("monitorIndex"),
        region=params.get("region"), format=params.get("format", "png")
    )


def handle_mouse_move(sid: str | None, bg: bool, hwnd: Any, params: Dict[str, Any]) -> Any:
    """Movimentação de mouse física ou em background."""
    if bg:
        return post_mouse_move(int(params["x"]), int(params["y"]), hwnd=hwnd, session_id=sid)
    return move_mouse(
        int(params["x"]), int(params["y"]),
        smooth=params.get("smooth", True), duration_ms=int(params.get("durationMs", 200))
    )


def handle_mouse_click(sid: str | None, bg: bool, hwnd: Any, params: Dict[str, Any]) -> Any:
    """Clique de mouse físico ou em background."""
    btn, dbl = params.get("button", "left"), bool(params.get("double", False))
    if bg:
        return post_mouse_click(
            button=btn, double=dbl, x=params.get("x"), y=params.get("y"), hwnd=hwnd, session_id=sid
        )
    return click_mouse(button=btn, double=dbl, hold_ms=int(params.get("holdMs", 50)))


def handle_mouse_drag(sid: str | None, bg: bool, hwnd: Any, params: Dict[str, Any]) -> Any:
    """Arraste de mouse físico ou em background."""
    sx, sy, ex, ey = int(params["startX"]), int(params["startY"]), int(params["endX"]), int(params["endY"])
    if bg:
        return post_mouse_drag(sx, sy, ex, ey, steps=int(params.get("steps", 10)), hwnd=hwnd, session_id=sid)
    return drag_mouse(sx, sy, ex, ey, steps=int(params.get("steps", 25)))


def handle_mouse_scroll(sid: str | None, bg: bool, hwnd: Any, params: Dict[str, Any]) -> Any:
    """Rolagem de mouse física ou em background."""
    dy, dx = int(params.get("deltaY", params.get("delta", 0))), int(params.get("deltaX", 0))
    if bg:
        return post_mouse_scroll(dy, dx, x=params.get("x"), y=params.get("y"), hwnd=hwnd, session_id=sid)
    return scroll_mouse(delta_y=dy, delta_x=dx)


def handle_keyboard_type(sid: str | None, bg: bool, hwnd: Any, params: Dict[str, Any]) -> Any:
    """Digitação no teclado física ou em background."""
    txt, dly = str(params["text"]), int(params.get("delayMs", 5))
    return post_keyboard_type(txt, delay_ms=dly, hwnd=hwnd, session_id=sid) if bg else type_text(txt, delay_ms=dly)


def handle_key_press(sid: str | None, bg: bool, hwnd: Any, params: Dict[str, Any]) -> Any:
    """Pressionamento de tecla físico ou em background."""
    k, mods = str(params["key"]), params.get("modifiers")
    return post_key_press(k, modifiers=mods, hwnd=hwnd, session_id=sid) if bg else press_key(k, modifiers=mods)


def handle_launch_app(sid: str | None, bg: bool, hwnd: Any, params: Dict[str, Any]) -> Any:
    """Inicialização de aplicativo desktop."""
    target = str(params.get("app", params.get("path", "excel")))
    os.startfile(target)
    return {"launched": target}


UNPROTECTED_ACTIONS: Dict[str, Callable[[str | None, Dict[str, Any]], Any]] = {
    "get_status": handle_status, "status": handle_status,
    "get_cursor": handle_cursor, "cursor": handle_cursor,
    "get_agent_cursor": handle_agent_cursor, "agent_cursor": handle_agent_cursor,
    "window_action": handle_window_action, "uia": handle_window_action,
}

PROTECTED_ACTIONS: Dict[str, Callable[[str | None, bool, Any, Dict[str, Any]], Any]] = {
    "screenshot": handle_screenshot, "screen": handle_screenshot,
    "mouse_move": handle_mouse_move, "move": handle_mouse_move,
    "mouse_click": handle_mouse_click, "click": handle_mouse_click,
    "mouse_drag": handle_mouse_drag, "drag": handle_mouse_drag,
    "mouse_scroll": handle_mouse_scroll, "scroll": handle_mouse_scroll,
    "keyboard_type": handle_keyboard_type, "type": handle_keyboard_type,
    "key_press": handle_key_press, "press_key": handle_key_press, "key": handle_key_press,
    "launch_app": handle_launch_app, "open_app": handle_launch_app, "launch": handle_launch_app,
}
