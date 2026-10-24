"""Registro e segregação de conexões WebSocket para extensões e agentes."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Set
logger = logging.getLogger("BrowserMTS.WSSessionRegistry")
try:
    from websockets.protocol import State
    _WS_STATE_OPEN = State.OPEN
except ImportError:
    _WS_STATE_OPEN = None
def is_socket_healthy(sock: Any) -> bool:
    """Verifica se o socket está conectado e em estado operacional aberto."""
    if sock is None:
        return False
    if hasattr(sock, "state"):
        if _WS_STATE_OPEN is not None:
            return sock.state == _WS_STATE_OPEN
        return getattr(sock.state, "name", "") == "OPEN"
    if getattr(sock, "closed", False):
        return False
    return True

class WSSessionRegistry:
    def __init__(self) -> None:
        self._extension_sockets: List[Any] = []
        self._agent_sockets: Set[Any] = set()
        self._session_sockets: Dict[str, Any] = {}
        self._session_instances: Dict[str, str] = {}
        self._client_info: Dict[Any, Dict[str, Any]] = {}
        self._active_socket: Any = None

    @property
    def is_connected(self) -> bool:
        return self.get_active_extension() is not None

    def get_active_extension(self) -> Optional[Any]:
        if self._active_socket is not None and is_socket_healthy(self._active_socket):
            return self._active_socket
        for sock in self._extension_sockets:
            if is_socket_healthy(sock):
                self._active_socket = sock
                return sock
        return None

    def get_socket_for_session(self, session_id: Optional[str]) -> Optional[Any]:
        if session_id:
            sock = self._session_sockets.get(str(session_id))
            if is_socket_healthy(sock):
                return sock
            if str(session_id) in self._session_instances:
                instance = self._session_instances[str(session_id)]
                if not instance: return None
                matches = [candidate for candidate in self._extension_sockets
                           if is_socket_healthy(candidate)
                           and str(self._client_info.get(candidate, {}).get("instanceId", "")) == instance]
                if len(matches) == 1:
                    self._session_sockets[str(session_id)] = matches[0]
                    return matches[0]
                return None
        return self.get_active_extension() if not session_id else None

    def select_socket(self, session_id: Optional[str], tab_id: Any = None) -> Optional[Any]:
        if session_id and str(session_id) in self._session_instances:
            return self.get_socket_for_session(session_id)
        sockets = [s for s in self._extension_sockets if is_socket_healthy(s)]
        if not sockets and is_socket_healthy(self._active_socket):
            sockets = [self._active_socket]
        if tab_id is not None:
            try: tid = int(tab_id)
            except (TypeError, ValueError): return None
            sockets = [s for s in sockets if tid in self._granted_ids(s)]
            if not sockets and len(self._extension_sockets) == 1:
                only = self._extension_sockets[0]
                if not self._client_info.get(only, {}).get("grantedTabIds") and is_socket_healthy(only):
                    sockets = [only]
        elif len(sockets) > 1:
            sockets = [s for s in sockets if self._granted_ids(s)]
        if len(sockets) != 1:
            return None
        sock = sockets[0]
        if session_id: self.bind_session_socket(session_id, sock)
        return sock

    def _granted_ids(self, websocket: Any) -> set[int]:
        raw = self._client_info.get(websocket, {}).get("grantedTabIds", [])
        if not isinstance(raw, (list, tuple, set)): return set()
        return {int(item) for item in raw if str(item).lstrip("-").isdigit()}

    def bind_session_socket(self, session_id: str, websocket: Any) -> None:
        if session_id and websocket:
            self._session_sockets[str(session_id)] = websocket
            instance = self._client_info.get(websocket, {}).get("instanceId")
            self._session_instances[str(session_id)] = str(instance or "")

    def register_extension(
        self, websocket: Any, info: Dict[str, Any], session_id: Optional[str] = None
    ) -> bool:
        self._client_info[websocket] = info
        if websocket not in self._extension_sockets:
            self._extension_sockets.append(websocket)

        sid = session_id or info.get("session_id") or info.get("sessionId")
        if sid:
            sid = str(sid)
            old = self._session_sockets.get(sid)
            if not old or not is_socket_healthy(old):
                self._session_sockets[sid] = websocket
                logger.info(f"Socket associado explicitamente à sessão '{sid}'.")
        instance = info.get("instanceId")
        if instance:
            for old_sid, old_instance in self._session_instances.items():
                old = self._session_sockets.get(old_sid)
                if old_instance == str(instance) and not is_socket_healthy(old):
                    self._session_sockets[old_sid] = websocket

        if self._active_socket is None or not is_socket_healthy(self._active_socket):
            self._active_socket = websocket

        logger.info(f"Extensão registrada. Total conectadas: {len(self._extension_sockets)}")
        return True

    def register_agent(self, websocket: Any) -> None:
        self._agent_sockets.add(websocket)
        logger.info(f"Socket de agente registrado. Total agentes: {len(self._agent_sockets)}")

    def unregister(self, websocket: Any) -> None:
        if websocket in self._extension_sockets:
            self._extension_sockets.remove(websocket)
        self._agent_sockets.discard(websocket)
        self._client_info.pop(websocket, None)
        dead_sessions = [s for s, sock in self._session_sockets.items() if sock == websocket]
        for s in dead_sessions:
            self._session_sockets.pop(s, None)
        if self._active_socket == websocket:
            self._active_socket = None
            self._active_socket = self.get_active_extension()
        logger.info(f"Socket removido. Extensões restantes: {len(self._extension_sockets)}")

    def get_info(self, websocket: Optional[Any] = None) -> Dict[str, Any]:
        target = websocket or self.get_active_extension()
        return self._client_info.get(target, {})

    def clear(self) -> None:
        self._extension_sockets.clear()
        self._agent_sockets.clear()
        self._session_sockets.clear()
        self._session_instances.clear()
        self._client_info.clear()
        self._active_socket = None
