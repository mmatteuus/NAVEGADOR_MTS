"""Ponte WebSocket Local (porta 3456) para comunicação com a Extensão do Navegador."""
import asyncio, json, logging, time, uuid
from typing import Any, Dict, Optional
from websockets.asyncio.server import Server, serve
from ..core.updater import APP_VERSION
from .extension_sync import ExtensionReloadPolicy

logger = logging.getLogger("BrowserMTS.WSBridge")


class WebSocketBridge:
    """Gerencia a ponte WebSocket local com a extensão do navegador."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3456) -> None:
        self.host, self.port = host, port
        self.server: Optional[Server] = None
        self._active_socket: Any = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self.client_info: Dict[str, Any] = {}
        self.last_latency_ms: float = 0.0
        self._reload_policy = ExtensionReloadPolicy(APP_VERSION)

    @property
    def is_connected(self) -> bool:
        """Verifica se há uma extensão de navegador conectada e ativa."""
        return self._active_socket is not None

    async def reload_extension(self) -> bool:
        """Envia ordem de recarga automática para a extensão atualizar em tempo real."""
        if self._active_socket:
            try:
                await self._active_socket.send(json.dumps({"type": "reload_extension"}))
                return True
            except Exception:
                pass
        return False

    async def start(self, max_ports: int = 10) -> int:
        """Inicia o servidor WebSocket local na porta configurada ou pula para uma livre se ocupada."""
        if self.server is not None:
            return self.port
        initial_port = self.port
        from ..core.config import current_config
        for offset in range(max_ports + 1):
            candidate_port = initial_port + offset
            if candidate_port == current_config.mcp_port:
                continue
            try:
                self.server = await serve(self._handle_client, self.host, candidate_port, reuse_address=True)
                self.port = candidate_port
                logger.info(f"WebSocket Bridge escutando em ws://{self.host}:{self.port}")
                return self.port
            except OSError as err:
                logger.warning(f"Porta {candidate_port} ocupada ({err}). Pulando para próxima porta...")
        raise RuntimeError(f"Nenhuma porta livre no intervalo {initial_port} a {initial_port + max_ports - 1}.")

    async def stop(self) -> None:
        """Encerra o servidor e cancela requisições pendentes com segurança."""
        for fut in self._pending_requests.values():
            if not fut.done(): fut.cancel()
        self._pending_requests.clear()
        if self._active_socket:
            await self._active_socket.close()
            self._active_socket = None
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def _handle_client(self, websocket: Any) -> None:
        """Processa o ciclo de vida e mensagens dos clientes conectados."""
        logger.info("Novo cliente conectado à ponte WebSocket.")
        try:
            async for raw_msg in websocket:
                await self._process_incoming_message(raw_msg, websocket)
        except Exception as exc:
            logger.warning(f"Conexão de cliente encerrada: {exc}")
        finally:
            if self._active_socket == websocket:
                self._active_socket = None
                logger.info("Extensão do navegador desconectada da ponte WebSocket.")
    async def _process_incoming_message(self, raw_msg: str, websocket: Any) -> None:
        """Interpreta envelopes JSON recebidos da extensão ou de agentes."""
        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            return
        msg_type = data.get("type")
        if msg_type == "client_hello":
            self._active_socket = websocket
            self.client_info = data.get("payload", {})
            reply = {
                "type": "server_hello",
                "payload": {"status": "connected", "desktopVersion": APP_VERSION, "heartbeatIntervalMs": 4000, "reloadRequired": self._reload_policy.should_reload(self.client_info)}
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
        elif msg_type == "agent_action":
            await self._handle_agent_action(data, websocket)
    async def _handle_agent_action(self, data: Dict[str, Any], websocket: Any) -> None:
        """Despacha uma ação enviada por um agente externo de IA."""
        act, params, call_id = data.get("action", ""), data.get("params", {}), data.get("id", "agent_cmd")
        try:
            if act.startswith("browser_"):
                res = await self.send_action(act, params)
                await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": True, "result": res}))
            elif act.startswith("computer_"):
                if act in ("computer_mouse_move", "computer_mouse_click",
                           "computer_mouse_drag", "computer_mouse_scroll",
                           "computer_keyboard_type", "computer_key_press"):
                    from ..computer import execute_computer_action
                    res = await asyncio.to_thread(execute_computer_action, act, params)
                else:
                    from .computer_dispatch import execute_mcp_computer
                    res = await execute_mcp_computer(act, params)
                await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": res.get("success", False), "result": res}))
            else:
                await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": False, "error": f"Ação desconhecida: '{act}'"}))
        except Exception as exc:
            await websocket.send(json.dumps({"id": call_id, "type": "agent_response", "success": False, "error": str(exc)}))
    def _resolve_pending_request(self, data: Dict[str, Any]) -> None:
        """Resolve a Future associada à resposta de uma ação enviada à extensão."""
        p = data.get("payload", {}) if "payload" in data else data
        req_id = p.get("requestId") or data.get("id")
        if req_id and req_id in self._pending_requests:
            fut = self._pending_requests.pop(req_id)
            if not fut.done():
                (fut.set_exception(RuntimeError(str(p["error"]))) if p.get("error")
                 else fut.set_result(p.get("result", p.get("data", {}))))
    async def send_action(self, action: str, params: Dict[str, Any], timeout: float = 30.0) -> Any:
        """Envia um comando para execução na extensão e aguarda a resposta."""
        if not self.is_connected:
            raise ConnectionError(f"Extensão do navegador não conectada na porta {self.port}.")
        req_id = f"cmd_{uuid.uuid4().hex[:12]}"
        fut = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = fut
        msg = {"id": req_id, "type": "execute_action", "action": action, "payload": params, "timestamp": int(time.time() * 1000)}
        await self._active_socket.send(json.dumps(msg))
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending_requests.pop(req_id, None)
