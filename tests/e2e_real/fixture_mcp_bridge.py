"""Servidor de QA E2E: inicializa WebSocketBridge e MCPServer em portas efêmeras."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.mcp.http_server import MCPHTTPServer
from src.mcp.server import MCPServer
from src.mcp.ws_bridge import WebSocketBridge

logging.basicConfig(level=logging.WARNING)


class QAMCPServer(MCPServer):
    """Servidor MCP compatível com parâmetros de sessão estendidos no transporte HTTP."""

    async def handle_jsonrpc(
        self, req: Dict[str, Any], session_id: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        # Se session_id vier do transporte HTTP e method for tools/call, repassa ao router
        if session_id and req.get("method") == "tools/call":
            params = req.get("params") or {}
            name = params.get("name", "")
            call_args = params.get("arguments") or {}
            res = await self.router.dispatch(name, call_args, session_id=session_id)
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": res}
        return await super().handle_jsonrpc(req)


class QAHTTPServer(MCPHTTPServer):
    """Extensão de MCPHTTPServer com controle de parada e rotas em porta efêmera."""

    def __init__(self, server: MCPServer, stop_event: asyncio.Event, bridge: WebSocketBridge) -> None:
        super().__init__(server, port=0, host="127.0.0.1")
        self.stop_event = stop_event
        self.bridge = bridge

    async def start(self) -> None:
        if self._runner is not None:
            return
        app = web.Application(client_max_size=1024 * 1024, middlewares=[self._validate_local_request])
        app.router.add_post("/mcp", self._post)
        app.router.add_get("/mcp", self._get)
        app.router.add_get("/healthz", self._health)

        async def stop_handler(_req: web.Request) -> web.Response:
            self.stop_event.set()
            return web.json_response({"stopping": True})

        async def status_handler(_req: web.Request) -> web.Response:
            return web.json_response({
                "connected": self.bridge.is_connected,
                "wsPort": self.bridge.port,
                "mcpPort": self.port,
            })

        app.router.add_post("/stop", stop_handler)
        app.router.add_get("/bridge-status", status_handler)

        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        self.port = site._server.sockets[0].getsockname()[1]
        self._runner = runner


async def main() -> None:
    """Inicia os subsistemas MCP e aguarda encerramento por timeout ou requisição."""
    bridge = WebSocketBridge(host="127.0.0.1", port=0)
    await bridge.start(max_ports=0)
    ws_port = bridge.server.sockets[0].getsockname()[1]

    mcp_server = QAMCPServer(host="127.0.0.1", ws_port=ws_port, ws_bridge=bridge)
    await mcp_server.start(start_ws=False)

    stop_event = asyncio.Event()
    http_server = QAHTTPServer(server=mcp_server, stop_event=stop_event, bridge=bridge)
    await http_server.start()

    payload = {"wsPort": ws_port, "mcpPort": http_server.port, "mcpUrl": f"http://127.0.0.1:{http_server.port}"}
    print(json.dumps(payload), flush=True)

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=180)
    except asyncio.TimeoutError:
        pass
    finally:
        await http_server.stop()
        await mcp_server.stop()
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
