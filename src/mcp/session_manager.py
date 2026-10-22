"""Gerenciador central de sessões isoladas e concorrência multissessão MCP."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
import uuid
from .session_models import AgentSession

logger = logging.getLogger("BrowserMTS.SessionManager")


class SessionManager:
    """Gerencia instâncias isoladas de AgentSession com locks refinados por agente."""

    def __init__(self) -> None:
        self._sessions: Dict[str, AgentSession] = {}
        self._registry_lock = asyncio.Lock()

    async def get_or_create_session(
        self, session_id: Optional[str] = None, agent_id: str = ""
    ) -> AgentSession:
        """Obtém ou cria atomicamente uma sessão de agente com lock granular."""
        sid = session_id.strip() if session_id and session_id.strip() else f"sess_{uuid.uuid4().hex[:12]}"
        async with self._registry_lock:
            if sid not in self._sessions:
                self._sessions[sid] = AgentSession(session_id=sid, agent_id=agent_id)
                logger.info(f"Nova sessão de agente criada: {sid} (agent={agent_id or 'default'})")
            return self._sessions[sid]

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Recupera uma sessão existente por ID ou None se inexistente."""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> bool:
        """Encerra uma sessão de agente e libera os recursos associados."""
        async with self._registry_lock:
            sess = self._sessions.pop(session_id, None)
            if sess:
                sess.status = "closed"
                logger.info(f"Sessão de agente encerrada: {session_id}")
                return True
            return False

    def list_active_sessions(self) -> List[str]:
        """Lista identificadores de todas as sessões ativas no momento."""
        return [sid for sid, s in self._sessions.items() if s.status == "active"]

    def validate_tab_access(self, session_id: Optional[str], tab_id: Any) -> bool:
        """Valida se a sessão solicitante tem permissão de acesso à aba alvo.

        Chamadas anônimas (session_id is None ou vazio) ou de outras sessões têm
        o acesso negado caso a aba pertença a qualquer sessão ativa registrada.
        """
        try:
            tid = int(tab_id)
        except (ValueError, TypeError):
            return False

        target_sid = session_id.strip() if session_id and session_id.strip() else None
        for sid, sess in self._sessions.items():
            if sess.status == "active" and sess.has_tab(tid) and sid != target_sid:
                logger.warning(
                    f"Acesso negado: aba {tid} pertence à sessão {sid} (solicitante: {target_sid or 'anônimo'})"
                )
                return False
        return True

    @staticmethod
    def extract_tab_id(response: Any) -> Optional[int]:
        """Extrai universalmente o ID da aba de respostas diretas ou envelopadas da extensão."""
        if isinstance(response, int):
            return response
        if not isinstance(response, dict):
            return None
        if response.get("tabId") is not None:
            try:
                return int(response["tabId"])
            except (ValueError, TypeError):
                pass
        for key in ("data", "result", "payload"):
            sub = response.get(key)
            if isinstance(sub, dict) and sub.get("tabId") is not None:
                try:
                    return int(sub["tabId"])
                except (ValueError, TypeError):
                    pass
            elif isinstance(sub, int):
                return sub
        return None

    def assign_tab_to_session(self, session_id: str, tab_id: int) -> None:
        """Vincula a aba informada à sessão do agente proprietário."""
        sess = self._sessions.get(session_id)
        if not sess:
            sess = AgentSession(session_id=session_id)
            self._sessions[session_id] = sess
        sess.assign_tab(tab_id)

    def release_tab(self, tab_id: int) -> None:
        """Libera a associação de uma aba em todas as sessões registradas."""
        for sess in self._sessions.values():
            sess.release_tab(tab_id)

    def clear(self) -> None:
        """Limpa todas as sessões registradas (útil para suítes de testes)."""
        self._sessions.clear()


session_manager = SessionManager()

__all__ = ["SessionManager", "session_manager"]
