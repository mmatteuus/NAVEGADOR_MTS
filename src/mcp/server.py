"""
Módulo Servidor Model Context Protocol Unificado (MCP Server).

Implementa o servidor MCP completo com suporte a transporte Stdio
(para Claude Desktop, Cursor e clientes de linha de comando) e integração
com a ponte WebSocket local para a extensão do navegador.
"""
import asyncio
import json
import logging
import sys
from typing import Any, Dict, Optional
from .router import MCPToolRouter
from .schemas_browser import get_browser_tools
from .schemas_computer import get_computer_tools
from .ws_bridge import WebSocketBridge

logger = logging.getLogger("BrowserMTS.MCPServer")


class MCPServer:
    """Servidor MCP principal com suporte a Stdio e WebSocket."""

    def __init__(self, host: str = "127.0.0.1", ws_port: int = 3456) -> None:
        self.host = host
        self.ws_port = ws_port
        self.name = "browser-mcp-mts"
        self.version = "2.0.0"
        self.ws_bridge = WebSocketBridge(host=self.host, port=self.ws_port)
        self.router = MCPToolRouter(ws_bridge=self.ws_bridge)
        self._running = False

    async def start(self, start_ws: bool = True) -> None:
        """Inicia os subsistemas do servidor MCP."""
        self._running = True
        if start_ws:
            await self.ws_bridge.start()
        logger.info(f"Servidor MCP '{self.name}' v{self.version} inicializado.")

    async def stop(self) -> None:
        """Encerra graciosamente todos os componentes do servidor."""
        self._running = False
        await self.ws_bridge.stop()
        logger.info("Servidor MCP finalizado.")

    async def handle_jsonrpc(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processa requisições JSON-RPC 2.0 da especificação Model Context Protocol."""
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            res = {
                "protocolVersion": "2024-11-05",
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
            args = params.get("arguments", {})
            call_res = await self.router.dispatch(name, args)
            return {"jsonrpc": "2.0", "id": req_id, "result": call_res}
        else:
            err = {"code": -32601, "message": f"Método não encontrado: '{method}'"}
            return {"jsonrpc": "2.0", "id": req_id, "error": err} if req_id is not None else None

    async def run_stdio(self) -> None:
        """Loop principal do transporte Stdio (lê de stdin e escreve em stdout)."""
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
                resp = await self.handle_jsonrpc(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except Exception as exc:
                sys.stderr.write(f"[{self.name}] Erro no loop Stdio: {exc}\n")
                sys.stderr.flush()
