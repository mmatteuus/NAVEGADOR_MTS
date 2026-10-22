"""Ponto de Entrada do Módulo Seguro de Computer Use do BROWSER MTS.

Centraliza as ferramentas de mouse, teclado, tela e segurança (física e background),
implementando o despachante universal execute_computer_action com trava Fail-Closed.
"""

from __future__ import annotations
import os
from typing import Any, Dict
from .safety_gate import SafetyGate, SecurityGateError, safety_gate
from .kill_switch import EmergencyKillSwitch, kill_switch
from .mouse import (
    click_mouse, drag_mouse, get_cursor_position,
    move_mouse, release_mouse_buttons, scroll_mouse,
    _physical_device_lock,
)
from .keyboard import press_key, release_all_keys, type_text
from .screen import capture_screen, get_monitors_info
from .window_finder import (
    ensure_thread_desktop, find_window_at, resolve_target_window, screen_to_client,
)
from .mouse_background import (
    get_agent_cursor_position, post_mouse_click, post_mouse_drag,
    post_mouse_move, post_mouse_scroll, reset_agent_cursors,
)
from .keyboard_background import post_key_press, post_keyboard_type

ensure_thread_desktop()

__all__ = [
    "safety_gate", "SafetyGate", "SecurityGateError",
    "kill_switch", "EmergencyKillSwitch",
    "move_mouse", "click_mouse", "drag_mouse", "scroll_mouse",
    "_physical_device_lock", "get_cursor_position", "release_mouse_buttons",
    "type_text", "press_key", "release_all_keys",
    "capture_screen", "get_monitors_info",
    "ensure_thread_desktop", "find_window_at", "screen_to_client", "resolve_target_window",
    "post_mouse_move", "post_mouse_click", "post_mouse_drag",
    "post_mouse_scroll", "get_agent_cursor_position", "reset_agent_cursors",
    "post_keyboard_type", "post_key_press",
    "execute_computer_action"
]


def execute_computer_action(action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Despacha uma ação do namespace computer_* com validação estrita de segurança."""
    params, act = params or {}, action.lower().replace("computer_", "")
    try:
        if act in ("get_status", "status"):
            return {
                "success": True,
                "data": {
                    "authorized": safety_gate.is_authorized(),
                    "killSwitchTriggered": safety_gate.is_kill_switch_triggered()
                }
            }
        try:
            from ..mcp.session_context import get_current_session_id
            ctx_sid = get_current_session_id()
        except Exception:
            ctx_sid = None
        sid = ctx_sid or params.get("session_id") or params.get("sessionId")
        if act in ("get_cursor", "cursor"):
            x, y = get_cursor_position()
            return {"success": True, "data": {"x": x, "y": y, "monitors": get_monitors_info()}}
        if act in ("get_agent_cursor", "agent_cursor"):
            ax, ay = get_agent_cursor_position(session_id=sid)
            return {"success": True, "data": {"x": ax, "y": ay, "sessionId": sid or "default"}}

        # Validação mandatória Fail-Closed antes de qualquer extração de parâmetros
        safety_gate.check_authorization(f"computer_{act}")
        bg, hwnd = bool(params.get("background", True)), params.get("hwnd")

        if act in ("screenshot", "screen"):
            return {
                "success": True,
                "data": capture_screen(
                    monitor_index=params.get("monitorIndex"),
                    region=params.get("region"), format=params.get("format", "png")
                )
            }
        if act in ("mouse_move", "move"):
            if bg:
                res = post_mouse_move(int(params["x"]), int(params["y"]), hwnd=hwnd, session_id=sid)
            else:
                res = move_mouse(
                    int(params["x"]), int(params["y"]),
                    smooth=params.get("smooth", True), duration_ms=int(params.get("durationMs", 200))
                )
            return {"success": True, "data": res}
        if act in ("mouse_click", "click"):
            btn, dbl = params.get("button", "left"), bool(params.get("double", False))
            if bg:
                res = post_mouse_click(
                    button=btn, double=dbl, x=params.get("x"), y=params.get("y"), hwnd=hwnd, session_id=sid
                )
            else:
                res = click_mouse(button=btn, double=dbl, hold_ms=int(params.get("holdMs", 50)))
            return {"success": True, "data": res}
        if act in ("mouse_drag", "drag"):
            sx, sy, ex, ey = int(params["startX"]), int(params["startY"]), int(params["endX"]), int(params["endY"])
            if bg:
                res = post_mouse_drag(
                    sx, sy, ex, ey, steps=int(params.get("steps", 10)), hwnd=hwnd, session_id=sid
                )
            else:
                res = drag_mouse(sx, sy, ex, ey, steps=int(params.get("steps", 25)))
            return {"success": True, "data": res}
        if act in ("mouse_scroll", "scroll"):
            dy = int(params.get("deltaY", params.get("delta", 0)))
            dx = int(params.get("deltaX", 0))
            if bg:
                res = post_mouse_scroll(
                    dy, dx, x=params.get("x"), y=params.get("y"), hwnd=hwnd, session_id=sid
                )
            else:
                res = scroll_mouse(delta_y=dy, delta_x=dx)
            return {"success": True, "data": res}
        if act in ("keyboard_type", "type"):
            txt, dly = str(params["text"]), int(params.get("delayMs", 5))
            res = post_keyboard_type(txt, delay_ms=dly, hwnd=hwnd) if bg else type_text(txt, delay_ms=dly)
            return {"success": True, "data": res}
        if act in ("key_press", "press_key", "key"):
            k, mods = str(params["key"]), params.get("modifiers")
            res = post_key_press(k, modifiers=mods, hwnd=hwnd) if bg else press_key(k, modifiers=mods)
            return {"success": True, "data": res}
        if act in ("launch_app", "open_app", "launch"):
            target = str(params.get("app", params.get("path", "excel")))
            os.startfile(target)
            return {"success": True, "data": {"launched": target}}

        return {"success": False, "error": f"Ação de computador desconhecida: '{action}'"}
    except SecurityGateError as sge:
        return {"success": False, "error": str(sge), "isSecurityBlock": True}
    except Exception as exc:
        return {"success": False, "error": f"Falha na execução de '{action}': {str(exc)}"}
