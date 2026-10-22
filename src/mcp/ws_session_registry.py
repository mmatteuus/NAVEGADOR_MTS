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

    def register_extension(self, websocket: Any, info: Dict[str, Any]) -> bool:
        """Registra uma extensão conectada sem permitir sobrescrita indevida do socket ativo."""
        self._client_info[websocket] = info
        if websocket not in self._extension_sockets:
            self._extension_sockets.append(websocket)

        active = self.get_active_extension()
        if active is not None and active != websocket:
            logger.warning(
                "Tentativa de sobrescrita de extensão ativa rejeitada: "
                "canal já ocupado por socket saudável."
            )
            return False

        self._active_socket = websocket
        logger.info(f"Extensão registrada como ativa. Total conectadas: {len(self._extension_sockets)}")
        return True

    def register_agent(self, websocket: Any) -> None:
        """Registra um socket de agente externo de IA."""
        self._agent_sockets.add(websocket)
        logger.info(f"Socket de agente registrado. Total agentes: {len(self._agent_sockets)}")

    def unregister(self, websocket: Any) -> None:
        """Remove um socket encerrado e atualiza a referência ativa."""
        if websocket in self._extension_sockets:
            self._extension_sockets.remove(websocket)
        self._agent_sockets.discard(websocket)
        self._client_info.pop(websocket, None)
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
        self._client_info.clear()
        self._active_socket = None
