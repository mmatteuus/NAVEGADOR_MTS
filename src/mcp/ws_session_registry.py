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
    if getattr(sock, "closed", False):
        return False
    return True


class WSSessionRegistry:
    """Gerencia conexões simultâneas segregando extensões e agentes de IA."""

    def __init__(self) -> None:
        self._extension_sockets: List[Any] = []
        self._agent_sockets: Set[Any] = set()
        self._session_sockets: Dict[str, Any] = {}
        self._client_info: Dict[Any, Dict[str, Any]] = {}
        self._active_socket: Any = None

    @property
    def is_connected(self) -> bool:
        """Indica se há ao menos uma extensão do navegador conectada e saudável."""
        return self.get_active_extension() is not None

    def get_active_extension(self) -> Optional[Any]:
        """Retorna o socket ativo e saudável da extensão."""
        if self._active_socket is not None and is_socket_healthy(self._active_socket):
            return self._active_socket
        for sock in self._extension_sockets:
            if is_socket_healthy(sock):
                self._active_socket = sock
                return sock
        return None

    def get_socket_for_session(self, session_id: Optional[str]) -> Optional[Any]:
        """Retorna o socket exclusivo da sessão ou faz fallback para a extensão ativa."""
        if session_id:
            sock = self._session_sockets.get(str(session_id))
            if is_socket_healthy(sock):
                return sock
        return self.get_active_extension()

    def bind_session_socket(self, session_id: str, websocket: Any) -> None:
        """Vincula dinamicamente um identificador de sessão a um socket de extensão."""
        if session_id and websocket:
            self._session_sockets[str(session_id)] = websocket

    def register_extension(
        self, websocket: Any, info: Dict[str, Any], session_id: Optional[str] = None
    ) -> bool:
        """Registra uma extensão conectada com suporte a múltiplos sockets indexados por sessão."""
        self._client_info[websocket] = info
        if websocket not in self._extension_sockets:
            self._extension_sockets.append(websocket)

        sid = session_id or info.get("session_id") or info.get("sessionId")
        if sid:
            self._session_sockets[str(sid)] = websocket
            logger.info(f"Socket associado explicitamente à sessão '{sid}'.")

        if self._active_socket is None or not is_socket_healthy(self._active_socket):
            self._active_socket = websocket

        logger.info(f"Extensão registrada. Total conectadas: {len(self._extension_sockets)}")
        return True

    def register_agent(self, websocket: Any) -> None:
        """Registra um socket de agente externo de IA."""
        self._agent_sockets.add(websocket)
        logger.info(f"Socket de agente registrado. Total agentes: {len(self._agent_sockets)}")

    def unregister(self, websocket: Any) -> None:
        """Remove um socket encerrado e atualiza a referência ativa e sessões vinculadas."""
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
        """Obtém os metadados do cliente para o socket especificado ou ativo."""
        target = websocket or self.get_active_extension()
        return self._client_info.get(target, {})

    def clear(self) -> None:
        """Limpa todos os registros de conexões ativas."""
        self._extension_sockets.clear()
        self._agent_sockets.clear()
        self._session_sockets.clear()
        self._client_info.clear()
        self._active_socket = None
