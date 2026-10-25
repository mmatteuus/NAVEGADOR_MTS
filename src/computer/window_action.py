"""Executor isolado das operações públicas UI Automation."""

from __future__ import annotations

from typing import Any, Optional

from .safety_gate import safety_gate
from . import uia_semantic


def execute(session_id: Optional[str], params: dict[str, Any]) -> dict[str, Any]:
    safety_gate.check_authorization("computer_window_action")
    if not session_id:
        raise ValueError("TARGET_NOT_ASSIGNED: sessão MCP obrigatória")
    operation = str(params.get("operation", "inspect"))
    selector = params.get("selector") or {}
    hwnd = params.get("hwnd")
    if operation == "inspect":
        return uia_semantic.inspect(session_id, hwnd)
    if operation == "invoke":
        return uia_semantic.invoke(session_id, selector, hwnd)
    if operation == "set_value":
        return uia_semantic.set_value(session_id, selector, params.get("value", ""), hwnd)
    if operation == "read_value":
        return uia_semantic.read_value(session_id, selector, hwnd)
    raise ValueError("UIA_OPERATION_UNSUPPORTED: use inspect, invoke, set_value ou read_value")
