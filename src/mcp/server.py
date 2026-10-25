"""
Módulo Servidor Model Context Protocol Unificado (MCP Server).

Implementa o servidor MCP completo com suporte a transporte Stdio
(para Claude Desktop, Cursor e clientes de linha de comando) e integração
com a ponte WebSocket local para a extensão do navegador.
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Any, Callable, Dict, Optional
from .router import MCPToolRouter
from .schemas_browser import get_browser_tools
from .schemas_computer import get_computer_tools
from .ws_bridge import WebSocketBridge

logger = logging.getLogger("BrowserMTS.MCPServer")


class MCPServer:
    """Servidor MCP principal com suporte a Stdio e WebSocket."""

    def __init__(self, host: str = "127.0.0.1", ws_port: int = 3456,
                 ws_bridge: Optional[WebSocketBridge] = None) -> None:
        self.host = host
        self.ws_port = ws_port
        self.name = "browser-mcp-mts"
        from ..core.updater import APP_VERSION
        self.version = APP_VERSION
        self.ws_bridge = ws_bridge or WebSocketBridge(host=self.host, port=self.ws_port)
        self._owns_bridge = ws_bridge is None
        from ..computer.safety_gate import safety_gate
        from .computer_dispatch import execute_mcp_computer
        self.router = MCPToolRouter(
            ws_bridge=self.ws_bridge, safety_checker=safety_gate.is_authorized,
            kill_switch_checker=safety_gate.is_kill_switch_triggered,
            computer_executor=execute_mcp_computer)
        self._running = False
        self._use_active_hub = False
        self.process_session_id = f"stdio_{os.getpid()}_{uuid.uuid4().hex[:8]}"

    async def start(self, start_ws: bool = True) -> None:
        """Inicia os subsistemas do servidor MCP conectando ao hub central ou subindo ponte."""
        self._running = True
        if start_ws and self._owns_bridge:
            from .hub_client import is_hub_running
            if await is_hub_running(self.host, self.ws_port):
                self._use_active_hub = True
                logger.info(f"Hub BROWSER MTS ativo detectado em {self.host}:{self.ws_port}. Encaminhando chamadas.")
            else:
                await self.ws_bridge.start()
        logger.info(f"Servidor MCP '{self.name}' v{self.version} inicializado.")

    async def stop(self) -> None:
        """Encerra graciosamente todos os componentes do servidor."""
        self._running = False
        if self._owns_bridge and not self._use_active_hub:
            await self.ws_bridge.stop()
        logger.info("Servidor MCP finalizado.")

    async def handle_jsonrpc(
        self, req: Dict[str, Any], session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Processa requisições JSON-RPC 2.0 da especificação Model Context Protocol."""
        effective_sid = session_id or self.process_session_id
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}
        if not isinstance(params, dict):
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32602, "message": "Parâmetros inválidos"}}

        if method == "initialize":
            from .agent_directory import initialize_agent
            await initialize_agent(self, effective_sid, params)
            res = {
                "protocolVersion": params.get("protocolVersion") if params.get("protocolVersion") in (
                    "2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"
                ) else "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": self.name, "version": self.version}
            }
            return {"jsonrpc": "2.0", "id": req_id, "result": res}
        elif method == "notifications/initialized":
            return None
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        elif method == "tools/list":
            tools = get_browser_tools() + get_computer_tools()
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments") or {}
            if not isinstance(args, dict):
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32602, "message": "Argumentos inválidos"}}
            if self._use_active_hub:
                from .hub_client import forward_tool_to_hub
                call_res = await forward_tool_to_hub(
                    name, args, host=self.host, port=self.ws_port, session_id=effective_sid
                )
            else:
                call_res = await self.router.dispatch(name, args, session_id=effective_sid)
            return {"jsonrpc": "2.0", "id": req_id, "result": call_res}
        else:
            err = {"code": -32601, "message": f"Método não encontrado: '{method}'"}
            return {"jsonrpc": "2.0", "id": req_id, "error": err} if req_id is not None else None

    async def run_stdio(self) -> None:
        """Loop principal do transporte Stdio (lê de stdin e escreve em stdout)."""
        from .session_context import set_current_session_id
        set_current_session_id(self.process_session_id)
        loop = asyncio.get_running_loop()
        sys.stderr.write(f"[{self.name}] Transporte Stdio pronto para conexões.\n")
        sys.stderr.flush()

        while self._running:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                req = json.loads(line)
                resp = await self.handle_jsonrpc(req, session_id=self.process_session_id)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except Exception as exc:
                sys.stderr.write(f"[{self.name}] Erro no loop Stdio: {exc}\n")
                sys.stderr.flush()
