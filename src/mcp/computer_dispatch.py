"""Adapta esquemas MCP às ações nativas sem contornar a trava de segurança."""
from __future__ import annotations

import asyncio
from typing import Any, Callable


def _plan(name: str, args: dict[str, Any]) -> list[tuple[str, dict]]:
    """Valida argumentos e devolve uma sequência de operações Win32."""
    if not isinstance(args, dict):
        raise ValueError("Argumentos MCP devem ser um objeto JSON.")
    if name in ("computer_screenshot", "computer_get_status", "computer_launch_app"):
        return [(name, args)]
    if name == "computer_mouse_action":
        action = args.get("action")
        if action == "move":
            return [("computer_mouse_move", {"x": args["x"], "y": args["y"]})]
        if action == "drag":
            return [("computer_mouse_drag", {
                "startX": args["x"], "startY": args["y"],
                "endX": args["end_x"], "endY": args["end_y"]})]
        buttons = {"click": "left", "double_click": "left",
                   "right_click": "right", "middle_click": "middle"}
        if action in buttons:
            ops = []
            if "x" in args or "y" in args:
                ops.append(("computer_mouse_move", {"x": args["x"], "y": args["y"]}))
            ops.append(("computer_mouse_click", {
                "button": args.get("button", buttons[action]),
                "double": action == "double_click"}))
            return ops
        raise ValueError(f"Ação de mouse não suportada: {action!r}")
    if name == "computer_keyboard_action":
        action = args.get("action")
        if action == "type":
            return [("computer_keyboard_type", {"text": args["text"]})]
        if action == "press":
            return [("computer_key_press", {"key": args["key"]})]
        if action == "hotkey":
            keys = args.get("keys")
            if not isinstance(keys, list) or not keys or not all(
                isinstance(k, str) and k for k in keys
            ):
                raise ValueError("Hotkey requer lista não vazia de teclas.")
            return [("computer_key_press", {
                "key": keys[-1], "modifiers": keys[:-1]})]
        raise ValueError(f"Ação de teclado não suportada: {action!r}")
    raise ValueError(f"Ferramenta de computador desconhecida: {name!r}")


async def execute_mcp_computer(
    name: str, args: dict[str, Any],
    executor: Callable[[str, dict], dict] | None = None,
) -> dict:
    """Executa no thread pool; o executor nativo também exige SafetyGate."""
    if executor is None:
        from ..computer import execute_computer_action
        executor = execute_computer_action
    try:
        operations = _plan(name, args)
        result = {}
        for operation, params in operations:
            result = await asyncio.to_thread(executor, operation, params)
            if not isinstance(result, dict) or not result.get("success", False):
                return result
        return result
    except (KeyError, TypeError, ValueError) as exc:
        return {"success": False, "error": f"Argumentos inválidos: {exc}"}
