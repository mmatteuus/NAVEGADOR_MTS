"""Ponto de Entrada do Módulo Seguro de Computer Use do BROWSER MTS.

Centraliza as ferramentas de mouse, teclado, tela e segurança (física e background),
implementando o despachante universal execute_computer_action com trava Fail-Closed.
"""

from __future__ import annotations
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
from .window_assignments import window_assignments
from .action_dispatcher import (
    PROTECTED_ACTIONS, UNPROTECTED_ACTIONS, get_session_id,
)

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
        if act in UNPROTECTED_ACTIONS:
            sid = get_session_id(params) if act not in ("get_status", "status") else None
            return {"success": True, "data": UNPROTECTED_ACTIONS[act](sid, params)}

        if act in PROTECTED_ACTIONS:
            sid = get_session_id(params)
            safety_gate.check_authorization(f"computer_{act}")
            bg, hwnd = bool(params.get("background", True)), params.get("hwnd")
            if sid and not bg:
                raise ValueError("PHYSICAL_INPUT_FORBIDDEN: sessão remota exige modo background")
            if bg and sid:
                hwnd = window_assignments.resolve(sid, hwnd)
            return {"success": True, "data": PROTECTED_ACTIONS[act](sid, bg, hwnd, params)}

        return {"success": False, "error": f"Ação de computador desconhecida: '{action}'"}
    except SecurityGateError as sge:
        return {"success": False, "error": str(sge), "isSecurityBlock": True}
    except Exception as exc:
        return {"success": False, "error": f"Falha na execução de '{action}': {str(exc)}"}
