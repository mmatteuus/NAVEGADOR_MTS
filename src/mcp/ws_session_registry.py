"""Registro e segregação de conexões WebSocket para extensões e agentes."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .ws_browser_targets import assigned_sockets, granted_ids, open_ids, select_candidate_socket
from .ws_socket_health import is_socket_healthy

logger = logging.getLogger("BrowserMTS.WSSessionRegistry")


class WSSessionRegistry:
    """Gerencia conexões de extensões de navegador e agentes de IA."""

    def __init__(self) -> None:
        self._extension_sockets, self._agent_sockets = [], set()
        self._session_sockets, self._session_instances = {}, {}
        self._client_info, self._active_socket = {}, None

    @property
    def is_connected(self) -> bool:
        return self.get_active_extension() is not None

    def extension_sockets(self) -> list[Any]:
        return [sock for sock in self._extension_sockets if is_socket_healthy(sock)]

    def get_active_extension(self) -> Optional[Any]:
        """Obtém a extensão ativa atual ou encontra uma saudável."""
        if self._active_socket is not None and is_socket_healthy(self._active_socket):
            return self._active_socket
        for sock in self._extension_sockets:
            if is_socket_healthy(sock):
                self._active_socket = sock
                return sock
        return None

    def get_socket_for_session(self, session_id: Optional[str]) -> Optional[Any]:
        """Recupera o socket saudável correspondente à sessão."""
        if not session_id:
            return self.get_active_extension()
        sock = self._session_sockets.get(str(session_id))
        if is_socket_healthy(sock):
            return sock
        if str(session_id) in self._session_instances:
            instance = self._session_instances[str(session_id)]
            if instance is None:
                return None
            matches = [
                c for c in self._extension_sockets
                if is_socket_healthy(c) and str(self._client_info.get(c, {}).get("instanceId", "")) == instance
            ]
            if len(matches) == 1:
                self._session_sockets[str(session_id)] = matches[0]
                return matches[0]
            if len(matches) > 1:
                logger.debug("Múltiplas extensões para a sessão %s", session_id)
        return None

    def select_socket(self, session_id: Optional[str], tab_id: Any = None) -> Optional[Any]:
        """Escolhe o socket correto usando a sessão e/ou a aba."""
        healthy = self.extension_sockets()
        assigned = assigned_sockets(healthy, self._client_info, session_id, tab_id)
        if len(assigned) == 1:
            if session_id: self.bind_session_socket(session_id, assigned[0])
            return assigned[0]
        if len(assigned) > 1:
            return None
        if session_id and str(session_id) in self._session_instances:
            bound = self.get_socket_for_session(session_id)
            if bound is not None:
                if tab_id is None or len(healthy) <= 1:
                    return bound
                alt = select_candidate_socket(healthy, self._client_info, session_id, tab_id, self._active_socket)
                if alt is not None and alt is not bound:
                    self.bind_session_socket(session_id, alt)
                    return alt
                return bound
            if not self._clear_orphan_session(str(session_id), healthy, tab_id):
                return None
        sockets = healthy or ([self._active_socket] if is_socket_healthy(self._active_socket) else [])
        sock = select_candidate_socket(sockets, self._client_info, session_id, tab_id, self._active_socket)
        if sock is None and tab_id is not None:
            logger.warning("Nenhuma extensão possui autorização para a aba especificada: %s", tab_id)
        if sock is not None and session_id:
            self.bind_session_socket(session_id, sock)
        return sock

    def _clear_orphan_session(self, sid: str, healthy: list[Any], tab_id: Any) -> bool:
        instance = self._session_instances.get(sid)
        if not instance or any(str(self._client_info.get(s, {}).get("instanceId", "")) == instance for s in self._extension_sockets):
            return False
        if select_candidate_socket(healthy, self._client_info, sid, tab_id, self._active_socket) is None:
            return False
        self._session_instances.pop(sid, None); self._session_sockets.pop(sid, None)
        return True

    def _granted_ids(self, websocket: Any) -> set[int]: return granted_ids(websocket, self._client_info)
    def _open_ids(self, websocket: Any) -> set[int]: return open_ids(websocket, self._client_info)

    def bind_session_socket(self, session_id: str, websocket: Any) -> None:
        if session_id and websocket:
            self._session_sockets[str(session_id)] = websocket
            instance = self._client_info.get(websocket, {}).get("instanceId")
            self._session_instances[str(session_id)] = str(instance) if instance is not None else None

    def register_extension(self, websocket: Any, info: Dict[str, Any], session_id: Optional[str] = None) -> bool:
        """Registra e ativa uma nova extensão, substituindo conexões anteriores da mesma instância."""
        instance = info.get("instanceId")
        if instance:
            inst_str = str(instance)
            stale = [s for s in self._extension_sockets if s is not websocket and str(self._client_info.get(s, {}).get("instanceId", "")) == inst_str]
            for old_sock in stale:
                self._extension_sockets.remove(old_sock); self._client_info.pop(old_sock, None)
                if self._active_socket is old_sock: self._active_socket = websocket
            for old_sid, old_inst in list(self._session_instances.items()):
                if old_inst == inst_str or self._session_sockets.get(old_sid) in stale:
                    self._session_sockets[old_sid] = websocket
        self._client_info[websocket] = info
        if websocket not in self._extension_sockets: self._extension_sockets.append(websocket)
        sid = session_id or info.get("session_id") or info.get("sessionId")
        if sid and (not self._session_sockets.get(str(sid)) or not is_socket_healthy(self._session_sockets.get(str(sid)))):
            self._session_sockets[str(sid)] = websocket
        if self._active_socket is None or not is_socket_healthy(self._active_socket):
            self._active_socket = websocket
        return True

    def register_agent(self, websocket: Any) -> None: self._agent_sockets.add(websocket)

    def unregister(self, websocket: Any) -> None:
        if websocket in self._extension_sockets: self._extension_sockets.remove(websocket)
        self._agent_sockets.discard(websocket); self._client_info.pop(websocket, None)
        for s in [s for s, sock in self._session_sockets.items() if sock == websocket]: self._session_sockets.pop(s, None)
        if self._active_socket == websocket: self._active_socket = self.get_active_extension()

    def get_info(self, websocket: Optional[Any] = None) -> Dict[str, Any]:
        return self._client_info.get(websocket or self.get_active_extension(), {})

    def clear(self) -> None:
        self._extension_sockets.clear(); self._agent_sockets.clear(); self._session_sockets.clear()
        self._session_instances.clear(); self._client_info.clear(); self._active_socket = None
