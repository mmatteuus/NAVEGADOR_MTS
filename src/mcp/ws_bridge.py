"""Ponte WebSocket Local (porta 3456) para comunicação com Extensão e Agentes."""
from __future__ import annotations
import asyncio, json, logging, time, uuid
from typing import Any, Dict, Optional
from websockets.asyncio.server import Server, serve
from ..core.updater import APP_VERSION
from .extension_sync import ExtensionReloadPolicy
from .ws_action_dispatcher import handle_incoming_envelope
from .ws_session_registry import WSSessionRegistry

logger = logging.getLogger("BrowserMTS.WSBridge")


class WebSocketBridge:
    """Gerencia a ponte WebSocket local com a extensão e múltiplos agentes."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3456) -> None:
        self.host, self.port = host, port
        self.server: Optional[Server] = None
        self.registry = WSSessionRegistry()
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_sockets: Dict[str, Any] = {}
        self._agent_sessions: Dict[Any, str] = {}
        self.last_latency_ms: float = 0.0
        self._reload_policy = ExtensionReloadPolicy(APP_VERSION)

    @property
    def _active_socket(self) -> Any: return self.registry.get_active_extension()
    @_active_socket.setter
    def _active_socket(self, val: Any) -> None: self.registry._active_socket = val
    @property
    def client_info(self) -> Dict[str, Any]: return self.registry.get_info()
    @property
    def is_connected(self) -> bool: return self.registry.is_connected

    async def reload_extension(self) -> bool:
        sock = self.registry.get_active_extension()
        if sock:
            try:
                await sock.send(json.dumps({"type": "reload_extension", "payload": {"desktopVersion": APP_VERSION}}))
                return True
            except Exception: pass
        return False

    async def start(self, max_ports: int = 10) -> int:
        if self.server is not None: return self.port
        initial_port = self.port
        from ..core.config import current_config
        for offset in range(max_ports + 1):
            candidate_port = initial_port + offset
            if candidate_port == current_config.mcp_port: continue
            try:
                self.server = await serve(self._handle_client, self.host, candidate_port, reuse_address=True)
                self.port = candidate_port
                logger.info(f"WebSocket Bridge escutando em ws://{self.host}:{self.port}")
                return self.port
            except OSError as err:
                logger.warning(f"Porta {candidate_port} ocupada ({err}). Pulando...")
        raise RuntimeError(f"Nenhuma porta livre no intervalo {initial_port} a {initial_port + max_ports - 1}.")

    async def stop(self) -> None:
        for fut in self._pending_requests.values():
            if not fut.done(): fut.cancel()
        self._pending_requests.clear()
        self._request_sockets.clear()
        self._agent_sessions.clear()
        sock = self.registry.get_active_extension()
        if sock: await sock.close()
        self.registry.clear()
        if self.server:
            self.server.close()
            await self.server.wait_closed(); await asyncio.sleep(0.01)
            self.server = None

    async def _handle_client(self, websocket: Any) -> None:
        try:
            async for raw in websocket: await self._process_incoming_message(raw, websocket)
        except Exception as exc: logger.warning(f"Conexão encerrada: {exc}")
        finally:
            self.registry.unregister(websocket)
            self._agent_sessions.pop(websocket, None)
            for request, owner in list(self._request_sockets.items()):
                future = self._pending_requests.get(request)
                if owner is websocket and future and not future.done():
                    future.set_exception(ConnectionError("EXTENSION_DISCONNECTED: conexão encerrada durante a ação."))

    async def _process_incoming_message(self, raw_msg: str, websocket: Any) -> None:
        try: data = json.loads(raw_msg)
        except json.JSONDecodeError: return
        await handle_incoming_envelope(data, websocket, self)

    async def send_action(
        self, action: str, params: Dict[str, Any], timeout: float = 30.0, session_id: Optional[str] = None
    ) -> Any:
        tab_id = params.get("tabId") if isinstance(params, dict) else None
        sock = self.registry.select_socket(session_id, tab_id)
        if not sock:
            if self.registry.is_connected:
                raise ConnectionError("BROWSER_SELECTION_REQUIRED: selecione uma aba no popup do navegador.")
            raise ConnectionError(f"EXTENSION_NOT_CONNECTED: Extensão do navegador não conectada na porta {self.port}.")
        req_id, fut = f"cmd_{uuid.uuid4().hex[:12]}", asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = fut
        self._request_sockets[req_id] = sock
        msg = {"id": req_id, "type": "execute_action", "action": action, "payload": params, "timestamp": int(time.time() * 1000)}
        if session_id: msg["sessionId"] = session_id
        try:
            await sock.send(json.dumps(msg))
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending_requests.pop(req_id, None)
            self._request_sockets.pop(req_id, None)
