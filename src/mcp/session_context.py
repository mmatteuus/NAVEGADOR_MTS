"""Contexto assíncrono de sessão MCP vinculado à camada de transporte (PEP 567).

Fornece armazenamento isolado por task assíncrona para o identificador da sessão
ativa emitido ou validado pelo transporte (HTTP Header ou Processo Stdio).
"""
from __future__ import annotations

import contextvars
from typing import Optional

_current_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "mcp_session_id", default=None
)


def get_current_session_id() -> Optional[str]:
    """Retorna o identificador de sessão ativo no transporte da requisição atual."""
    return _current_session_id.get()


def set_current_session_id(session_id: Optional[str]) -> contextvars.Token:
    """Define a sessão ativa para a task assíncrona atual e retorna o token de restauração."""
    sid = str(session_id).strip() if session_id and str(session_id).strip() else None
    return _current_session_id.set(sid)


def reset_current_session_id(token: contextvars.Token) -> None:
    """Restaura o contexto anterior da task utilizando o token fornecido."""
    _current_session_id.reset(token)


__all__ = ["get_current_session_id", "set_current_session_id", "reset_current_session_id"]
