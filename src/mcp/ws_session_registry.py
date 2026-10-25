"""Registro e segregação de conexões WebSocket para extensões e agentes."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("BrowserMTS.WSSessionRegistry")

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

class WSSessionRegistry:
    """Gerencia conexões de extensões de navegador e agentes de IA."""

    def __init__(self) -> None:
        self._extension_sockets, self._agent_sockets = [], set()
        self._session_sockets, self._session_instances = {}, {}
        self._client_info, self._active_socket = {}, None

    @property
    def is_connected(self) -> bool:
        """Retorna True se houver pelo menos uma extensão ativa saudável."""
        return self.get_active_extension() is not None

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
        if session_id and str(session_id) in self._session_instances:
            return self.get_socket_for_session(session_id)
        sockets = [s for s in self._extension_sockets if is_socket_healthy(s)]
        if not sockets and is_socket_healthy(self._active_socket):
            sockets = [self._active_socket]
        if tab_id is not None:
            try:
                tid = int(tab_id)
            except (TypeError, ValueError):
                return None
            sockets = [s for s in sockets if tid in self._granted_ids(s)]
            if not sockets and len(self._extension_sockets) == 1:
                only = self._extension_sockets[0]
                if not self._client_info.get(only, {}).get("grantedTabIds") and is_socket_healthy(only):
                    sockets = [only]
            if not sockets:
                logger.warning("Nenhuma extensão possui autorização para a aba especificada: %s", tab_id)
        elif len(sockets) > 1:
            sockets = [s for s in sockets if self._granted_ids(s)]
        if len(sockets) != 1:
            return None
        sock = sockets[0]
        if session_id:
            self.bind_session_socket(session_id, sock)
        return sock

    def _granted_ids(self, websocket: Any) -> set[int]:
        raw = self._client_info.get(websocket, {}).get("grantedTabIds", [])
        if not isinstance(raw, (list, tuple, set)):
            return set()
        return {int(item) for item in raw if str(item).lstrip("-").isdigit()}

    def bind_session_socket(self, session_id: str, websocket: Any) -> None:
        """Vincula a sessão a um socket de extensão."""
        if session_id and websocket:
            self._session_sockets[str(session_id)] = websocket
            instance = self._client_info.get(websocket, {}).get("instanceId")
            self._session_instances[str(session_id)] = str(instance) if instance is not None else None

    def register_extension(self, websocket: Any, info: Dict[str, Any], session_id: Optional[str] = None) -> bool:
        """Registra e ativa uma nova extensão com seus metadados."""
        self._client_info[websocket] = info
        if websocket not in self._extension_sockets:
            self._extension_sockets.append(websocket)
        sid = session_id or info.get("session_id") or info.get("sessionId")
        if sid:
            sid = str(sid)
            old = self._session_sockets.get(sid)
            if not old or not is_socket_healthy(old):
                self._session_sockets[sid] = websocket
        instance = info.get("instanceId")
        if instance:
            for old_sid, old_instance in self._session_instances.items():
                old = self._session_sockets.get(old_sid)
                if old_instance == str(instance) and not is_socket_healthy(old):
                    self._session_sockets[old_sid] = websocket
        if self._active_socket is None or not is_socket_healthy(self._active_socket):
            self._active_socket = websocket
        return True

    def register_agent(self, websocket: Any) -> None:
        """Adiciona socket de agente."""
        self._agent_sockets.add(websocket)

    def unregister(self, websocket: Any) -> None:
        """Remove extensão ou agente desconectado."""
        if websocket in self._extension_sockets: self._extension_sockets.remove(websocket)
        self._agent_sockets.discard(websocket); self._client_info.pop(websocket, None)
        for s in [s for s, sock in self._session_sockets.items() if sock == websocket]:
            self._session_sockets.pop(s, None)
        if self._active_socket == websocket: self._active_socket = self.get_active_extension()

    def get_info(self, websocket: Optional[Any] = None) -> Dict[str, Any]:
        """Retorna metadados da conexão."""
        return self._client_info.get(websocket or self.get_active_extension(), {})

    def clear(self) -> None:
        """Limpa estado."""
        self._extension_sockets.clear(); self._agent_sockets.clear()
        self._session_sockets.clear(); self._session_instances.clear()
        self._client_info.clear(); self._active_socket = None
