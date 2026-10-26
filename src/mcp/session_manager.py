"""Gerenciador central de sessões isoladas e concorrência multissessão MCP."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
import uuid
import psutil
from .session_models import AgentSession, classify_agent_family

logger = logging.getLogger("BrowserMTS.SessionManager")


class _ImmediateDone:
    """Permite usar métodos síncronos tanto diretamente quanto com await."""
    __slots__ = ("value",)

    def __init__(self, value: Any = None) -> None:
        self.value = value

    def __await__(self):
        if False:
            yield None
        return self.value


def _release_session_grants(session_id: str) -> None:
    """Libera janelas Win32 e diretórios concedidos quando a sessão encerra."""
    for mod_name, obj_name, method in (
        ("window_assignments", "window_assignments", "release"),
        ("folder_assignments", "folder_grants", "revoke"),
    ):
        try:
            mod = __import__(f"src.computer.{mod_name}", fromlist=[obj_name])
            getattr(getattr(mod, obj_name), method)(session_id)
        except Exception:
            pass


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
            elif agent_id and not self._sessions[sid].agent_id:
                self._sessions[sid].agent_id = agent_id
                self._sessions[sid].agent_family = classify_agent_family(agent_id)
            return self._sessions[sid]

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Recupera uma sessão existente por ID ou None se inexistente."""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> bool:
        """Encerra uma sessão de agente e libera janelas e pastas associadas."""
        async with self._registry_lock:
            sess = self._sessions.pop(session_id, None)
            if sess:
                sess.status = "closed"
                _release_session_grants(session_id)
                return True
            return False

    def prune_dead_sessions(self) -> List[str]:
        """Remove sessões cujo processo local (PID) não existe mais e libera concessões."""
        pruned: List[str] = []
        for sid, sess in list(self._sessions.items()):
            if sess.pid is not None and not psutil.pid_exists(sess.pid):
                self._sessions.pop(sid, None)
                sess.status = "closed"
                _release_session_grants(sid)
                pruned.append(sid)
        return pruned

    def list_active_sessions(self) -> List[str]:
        """Lista identificadores de todas as sessões ativas no momento."""
        return [sid for sid, s in self._sessions.items() if s.status == "active"]

    def validate_tab_access(self, session_id: Optional[str], tab_id: Any) -> bool:
        """Valida se a sessão solicitante tem permissão de acesso à aba alvo."""
        try:
            tid = int(tab_id)
        except (ValueError, TypeError):
            return False
        target_sid = session_id.strip() if session_id and session_id.strip() else None
        return not any(
            s.status == "active" and s.has_tab(tid) and sid != target_sid
            for sid, s in self._sessions.items()
        )

    @staticmethod
    def extract_tab_id(response: Any) -> Optional[int]:
        """Extrai universalmente o ID da aba de respostas diretas ou envelopadas da extensão."""
        if isinstance(response, int):
            return response
        if not isinstance(response, dict):
            return None
        for candidate in (response, *(response.get(k) for k in ("data", "result", "payload"))):
            if isinstance(candidate, dict) and candidate.get("tabId") is not None:
                try:
                    return int(candidate["tabId"])
                except (ValueError, TypeError):
                    pass
            elif isinstance(candidate, int) and candidate is not response:
                return candidate
        return None

    def assign_tab_to_session(self, session_id: str, tab_id: int) -> _ImmediateDone:
        """Vincula a aba informada à sessão do agente proprietário (compatível com sync e await)."""
        sess = self._sessions.setdefault(session_id, AgentSession(session_id=session_id))
        sess.assign_tab(int(tab_id))
        return _ImmediateDone(None)

    def release_tab(self, tab_id: int) -> None:
        """Libera a associação de uma aba em todas as sessões registradas."""
        for sess in self._sessions.values():
            sess.release_tab(tab_id)

    def clear(self) -> None:
        """Limpa todas as sessões registradas (útil para suítes de testes)."""
        self._sessions.clear()


session_manager = SessionManager()
__all__ = ["SessionManager", "session_manager"]
