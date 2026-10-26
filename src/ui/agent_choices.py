"""Rótulos humanos de sessões e validação no instante da concessão."""
from __future__ import annotations

from ..mcp.session_manager import session_manager

TUNNEL_DEFAULT_SESSION = "tunnel_default"
TUNNEL_DEFAULT_LABEL = "🌐 Agente do Navegador / Túnel (Chat Web)"


def choices() -> dict[str, str]:
    result = {TUNNEL_DEFAULT_LABEL: TUNNEL_DEFAULT_SESSION}
    for sid in session_manager.list_active_sessions():
        item = session_manager.get_session(sid)
        if item is not None and sid != TUNNEL_DEFAULT_SESSION:
            result[f"{item.agent_id or 'Agente'} ({sid})"] = sid
    return result


def require_active(session_id: str) -> None:
    sid = str(session_id or "").strip()
    if sid == TUNNEL_DEFAULT_SESSION:
        return
    item = session_manager.get_session(sid)
    if item is None or item.status != "active":
        raise ValueError("Selecione um agente conectado e atualize a lista")


def refresh_choices(widget) -> dict[str, str]:
    mapping = choices()
    values = list(mapping) or ["(nenhuma sessão)"]
    previous = widget.get()
    widget.configure(values=values, state="readonly")
    if previous in mapping:
        widget.set(previous)
    else:
        widget.set(TUNNEL_DEFAULT_LABEL if TUNNEL_DEFAULT_LABEL in mapping else values[0])
    return mapping
