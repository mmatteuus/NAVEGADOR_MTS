"""
Ponto de Entrada do Módulo Seguro de Computer Use do BROWSER MTS.

Centraliza as exportações das ferramentas de mouse, teclado, tela e segurança,
e implementa o despachante universal execute_computer_action conforme
especificado no contrato Model Context Protocol (MCP).
"""

from typing import Dict, Any
from .safety_gate import safety_gate, SafetyGate, SecurityGateError
from .kill_switch import kill_switch, EmergencyKillSwitch
from .mouse import (
    move_mouse, click_mouse, drag_mouse, scroll_mouse,
    get_cursor_position, release_mouse_buttons
)
from .keyboard import type_text, press_key, release_all_keys
from .screen import capture_screen, get_monitors_info

__all__ = [
    "safety_gate", "SafetyGate", "SecurityGateError",
    "kill_switch", "EmergencyKillSwitch",
    "move_mouse", "click_mouse", "drag_mouse", "scroll_mouse",
    "get_cursor_position", "release_mouse_buttons",
    "type_text", "press_key", "release_all_keys",
    "capture_screen", "get_monitors_info",
    "execute_computer_action"
]

def execute_computer_action(action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Despacha uma ação do namespace computer_* com validação estrita de segurança."""
    params = params or {}
    act = action.lower().replace("computer_", "")

    try:
        if act in ("get_status", "status"):
            return {
                "success": True,
                "data": {
                    "authorized": safety_gate.is_authorized(),
                    "killSwitchTriggered": safety_gate.is_kill_switch_triggered()
                }
            }

        if act in ("get_cursor", "cursor"):
            x, y = get_cursor_position()
            monitors = get_monitors_info()
            return {"success": True, "data": {"x": x, "y": y, "monitors": monitors}}

        # Validação obrigatória da trava Fail-Closed antes de qualquer extração de parâmetros
        if act not in ("get_status", "status", "get_cursor", "cursor"):
            safety_gate.check_authorization(f"computer_{act}")

        if act in ("screenshot", "screen"):
            result = capture_screen(
                monitor_index=params.get("monitorIndex"),
                region=params.get("region"),
                format=params.get("format", "png")
            )
            return {"success": True, "data": result}

        if act in ("mouse_move", "move"):
            result = move_mouse(
                x=int(params["x"]), y=int(params["y"]),
                smooth=params.get("smooth", True),
                duration_ms=int(params.get("durationMs", 200))
            )
            return {"success": True, "data": result}

        if act in ("mouse_click", "click"):
            result = click_mouse(
                button=params.get("button", "left"),
                double=bool(params.get("double", False)),
                hold_ms=int(params.get("holdMs", 50))
            )
            return {"success": True, "data": result}

        if act in ("mouse_drag", "drag"):
            result = drag_mouse(
                start_x=int(params["startX"]), start_y=int(params["startY"]),
                end_x=int(params["endX"]), end_y=int(params["endY"]),
                steps=int(params.get("steps", 25))
            )
            return {"success": True, "data": result}

        if act in ("mouse_scroll", "scroll"):
            result = scroll_mouse(
                delta_y=int(params.get("deltaY", 0)),
                delta_x=int(params.get("deltaX", 0))
            )
            return {"success": True, "data": result}

        if act in ("keyboard_type", "type"):
            result = type_text(
                text=str(params["text"]),
                delay_ms=int(params.get("delayMs", 25))
            )
            return {"success": True, "data": result}

        if act in ("key_press", "press_key", "key"):
            result = press_key(
                key=str(params["key"]),
                modifiers=params.get("modifiers")
            )
            return {"success": True, "data": result}

        return {
            "success": False,
            "error": f"Ação de computador desconhecida: '{action}'"
        }

    except SecurityGateError as sge:
        return {
            "success": False,
            "error": str(sge),
            "isSecurityBlock": True
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Falha na execução de '{action}': {str(exc)}"
        }
