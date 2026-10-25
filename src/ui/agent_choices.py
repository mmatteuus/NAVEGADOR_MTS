"""Rótulos humanos de sessões e validação no instante da concessão."""
from __future__ import annotations

from ..mcp.session_manager import session_manager


def choices() -> dict[str, str]:
    result = {}
    for sid in session_manager.list_active_sessions():
        item = session_manager.get_session(sid)
        if item is not None:
            result[f"{item.agent_id or 'Agente'} ({sid})"] = sid
    return result


def require_active(session_id: str) -> None:
    item = session_manager.get_session(session_id)
    if item is None or item.status != "active":
        raise ValueError("Selecione um agente conectado e atualize a lista")


def refresh_choices(widget) -> dict[str, str]:
    mapping = choices()
    values = list(mapping) or ["(nenhuma sessão)"]
    previous = widget.get()
    widget.configure(values=values, state="readonly")
    widget.set(previous if previous in mapping else values[0])
    return mapping
