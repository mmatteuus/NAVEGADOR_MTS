"""Adapta esquemas MCP às ações nativas sem contornar a trava de segurança."""
from __future__ import annotations

import asyncio
from typing import Any, Callable


def _enrich(payload: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    """Propaga background (default True) e hwnd aos parâmetros operacionais."""
    payload["background"] = args.get("background", True)
    if "hwnd" in args:
        payload["hwnd"] = args["hwnd"]
    for key in ("session_id", "sessionId"):
        if key in args:
            payload[key] = args[key]
    return payload


def _plan(name: str, args: dict[str, Any]) -> list[tuple[str, dict]]:
    """Valida argumentos e devolve uma sequência de operações Win32."""
    if not isinstance(args, dict):
        raise ValueError("Argumentos MCP devem ser um objeto JSON.")
    if name in ("computer_screenshot", "computer_get_status", "computer_launch_app", "computer_window_action"):
        return [(name, args)]
    if name == "computer_mouse_action":
        action = args.get("action")
        if action == "move":
            return [("computer_mouse_move", _enrich({"x": args["x"], "y": args["y"]}, args))]
        if action == "drag":
            payload = {
                "startX": args["x"], "startY": args["y"],
                "endX": args["end_x"], "endY": args["end_y"]
            }
            return [("computer_mouse_drag", _enrich(payload, args))]
        if action == "scroll":
            delta = args.get("delta", 0)
            payload = {"deltaY": delta, "delta": delta}
            for coord in ("x", "y"):
                if coord in args:
                    payload[coord] = args[coord]
            if "delta_x" in args or "deltaX" in args:
                payload["deltaX"] = args.get("delta_x", args.get("deltaX", 0))
            return [("computer_mouse_scroll", _enrich(payload, args))]
        buttons = {
            "click": "left", "double_click": "left",
            "right_click": "right", "middle_click": "middle"
        }
        if action in buttons:
            ops = []
            if "x" in args or "y" in args:
                ops.append(("computer_mouse_move", _enrich({"x": args["x"], "y": args["y"]}, args)))
            ops.append(("computer_mouse_click", _enrich({
                "button": buttons[action] if action in ("right_click", "middle_click")
                          else args.get("button", buttons[action]),
                "double": action == "double_click"
            }, args)))
            return ops
        raise ValueError(f"Ação de mouse não suportada: {action!r}")
    if name == "computer_keyboard_action":
        action = args.get("action")
        if action == "type":
            return [("computer_keyboard_type", _enrich({"text": args["text"]}, args))]
        if action == "press":
            return [("computer_key_press", _enrich({"key": args["key"]}, args))]
        if action == "hotkey":
            keys = args.get("keys")
            if not isinstance(keys, list) or not keys or not all(
                isinstance(k, str) and k for k in keys
            ):
                raise ValueError("Hotkey requer lista não vazia de teclas.")
            return [("computer_key_press", _enrich({
                "key": keys[-1], "modifiers": keys[:-1]
            }, args))]
        raise ValueError(f"Ação de teclado não suportada: {action!r}")
    raise ValueError(f"Ferramenta de computador desconhecida: {name!r}")


async def execute_mcp_computer(
    name: str, args: dict[str, Any],
    executor: Callable[[str, dict], dict] | None = None,
) -> dict:
    """Executa no thread pool; o executor nativo também exige SafetyGate."""
    try:
        if not isinstance(args, dict):
            raise ValueError("Argumentos MCP devem ser um objeto JSON.")
        if name == "computer_folder_action":
            from ..computer.folder_actions import execute_folder_action
            from .session_context import get_current_session_id
            sid = get_current_session_id() or args.get("sessionId")
            return await asyncio.to_thread(execute_folder_action, args, sid)
        if executor is None:
            from ..computer import execute_computer_action
            executor = execute_computer_action
        operations = _plan(name, args)
        result = {}
        for operation, params in operations:
            result = await asyncio.to_thread(executor, operation, params)
            if not isinstance(result, dict) or not result.get("success", False):
                return result
        return result
    except (KeyError, TypeError, ValueError) as exc:
        return {"success": False, "error": f"Argumentos inválidos: {exc}"}
