"""Identidade estável de um agente durante a conexão WebSocket local."""
from __future__ import annotations

import uuid


def resolve_agent_identity(bridge, websocket, requested=None) -> str:
    """Uma conexão não troca de sessão nem usa o destino global anônimo."""
    if requested is not None and (not isinstance(requested, str) or not requested.strip()
                                  or len(requested) > 160):
        raise ValueError("SESSION_INVALID: identificador de sessão inválido.")
    requested = requested.strip() if requested else None
    previous = bridge._agent_sessions.get(websocket)
    if previous and requested and previous != requested:
        raise ValueError("FORGERY_DENIED: uma conexão não pode assumir outra sessão.")
    sid = previous or requested or f"ws_{uuid.uuid4().hex}"
    bridge._agent_sessions[websocket] = sid
    return sid
