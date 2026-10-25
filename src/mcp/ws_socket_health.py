"""Inspeção do estado de uma conexão WebSocket."""
from __future__ import annotations
from typing import Any

def is_socket_healthy(sock: Any) -> bool:
    """Verifica se o socket está conectado e em estado operacional aberto."""
    if sock is None:
        return False
    if hasattr(sock, "state"):
        try:
            from websockets.protocol import State
            return sock.state == State.OPEN
        except Exception:
            return getattr(sock.state, "name", "") == "OPEN"
    return not getattr(sock, "closed", False)
