"""
Módulo de Ponte WebSocket Local (WebSocket Bridge).

Implementa o servidor WebSocket local (porta 3456) para comunicação
bidirecional entre o Servidor MCP Desktop e a Extensão do Navegador.
Suporta handshake de apresentação, ping-pong de 3s e despacho assíncrono.
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, Optional
from websockets.asyncio.server import Server, serve

logger = logging.getLogger("BrowserMTS.WSBridge")


class WebSocketBridge:
    """Gerencia a ponte WebSocket local com a extensão do navegador."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3456) -> None:
        self.host = host
        self.port = port
        self.server: Optional[Server] = None
        self._active_socket: Any = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self.client_info: Dict[str, Any] = {}
        self.last_latency_ms: float = 0.0

    @property
    def is_connected(self) -> bool:
        """Verifica se há uma extensão de navegador conectada e ativa."""
        return self._active_socket is not None

    async def start(self) -> None:
        """Inicia o servidor WebSocket local na porta configurada."""
        if self.server is not None:
            return
        self.server = await serve(self._handle_client, self.host, self.port, reuse_address=True)
        logger.info(f"WebSocket Bridge escutando em ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Encerra o servidor e cancela requisições pendentes com segurança."""
        for req_id, fut in list(self._pending_requests.items()):
            if not fut.done():
                fut.cancel()
        self._pending_requests.clear()
        if self._active_socket:
            await self._active_socket.close()
            self._active_socket = None
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def _handle_client(self, websocket: Any) -> None:
        """Processa o ciclo de vida e mensagens da extensão conectada."""
        self._active_socket = websocket
        logger.info("Extensão do navegador conectada à ponte WebSocket.")
        try:
            async for raw_msg in websocket:
                await self._process_incoming_message(raw_msg, websocket)
        except Exception as exc:
            logger.warning(f"Conexão com extensão encerrada: {exc}")
        finally:
            if self._active_socket == websocket:
                self._active_socket = None
            logger.info("Extensão desconectada da ponte WebSocket.")

    async def _process_incoming_message(self, raw_msg: str, websocket: Any) -> None:
        """Interpreta envelopes JSON recebidos da extensão."""
        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        if msg_type == "client_hello":
            self.client_info = data.get("payload", {})
            reply = {
                "type": "server_hello",
                "payload": {"status": "connected", "desktopVersion": "2.0.0", "heartbeatIntervalMs": 3000}
            }
            await websocket.send(json.dumps(reply))
        elif msg_type == "ping":
            ts = data.get("ts", int(time.time() * 1000))
            await websocket.send(json.dumps({"type": "pong", "ts": ts, "serverTs": int(time.time() * 1000)}))
        elif msg_type == "pong":
            client_ts = data.get("clientTs", 0)
            if client_ts > 0:
                self.last_latency_ms = max(0.0, (time.time() * 1000) - client_ts)
        elif msg_type in ("messageResponse", "browser_response"):
            self._resolve_pending_request(data)

    def _resolve_pending_request(self, data: Dict[str, Any]) -> None:
        """Resolve a Future associada à resposta de uma ação enviada à extensão."""
        payload = data.get("payload", {}) if "payload" in data else data
        req_id = payload.get("requestId") or data.get("id")
        if req_id and req_id in self._pending_requests:
            fut = self._pending_requests.pop(req_id)
            if not fut.done():
                if payload.get("error"):
                    fut.set_exception(RuntimeError(str(payload["error"])))
                else:
                    fut.set_result(payload.get("result", payload.get("data", {})))

    async def send_action(self, action: str, params: Dict[str, Any], timeout: float = 30.0) -> Any:
        """Envia um comando para execução na extensão e aguarda a resposta."""
        if not self.is_connected:
            raise ConnectionError("Extensão do navegador não conectada na porta 3456.")

        req_id = f"cmd_{uuid.uuid4().hex[:12]}"
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending_requests[req_id] = fut

        msg = {
            "id": req_id,
            "type": "execute_action",
            "action": action,
            "payload": params,
            "timestamp": int(time.time() * 1000)
        }
        await self._active_socket.send(json.dumps(msg))
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending_requests.pop(req_id, None)
