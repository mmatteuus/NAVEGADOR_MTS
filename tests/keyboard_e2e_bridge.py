"""Servidor descartável de QA: roteador MCP e ponte reais em portas dinâmicas."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.mcp.router import MCPToolRouter
from src.mcp.ws_bridge import WebSocketBridge

PAGE = """<!doctype html><meta charset="utf-8"><title>Teclado QA</title>
<style>body{font:18px sans-serif;padding:32px}input,textarea{display:block;margin:16px}</style>
<h1>Teste local de teclado independente</h1>
<label>Usuário<input id="user" value=""></label>
<form onsubmit="event.preventDefault();window.submissions=(window.submissions||0)+1">
<label>Agente<input id="agent" value=""></label><button>Enviar</button></form>
<textarea id="area"></textarea><div id="editable" contenteditable="true">abc</div>
<input type="checkbox" id="check"><div id="rich" contenteditable="true"><b>rico</b></div>
"""


async def main() -> None:
    """Atende somente loopback; nunca conecta a instâncias de produção."""
    bridge = WebSocketBridge(port=0)
    await bridge.start(max_ports=0)
    port = bridge.server.sockets[0].getsockname()[1]
    router = MCPToolRouter(ws_bridge=bridge)
    stop = asyncio.Event()

    async def page(_request):
        return web.Response(text=PAGE, content_type="text/html")

    async def command(request):
        body = await request.json()
        return web.json_response(await router.dispatch(body["name"], body.get("args", {})))

    async def status(_request):
        return web.json_response({"connected": bridge.is_connected, "wsPort": port})

    async def shutdown(_request):
        stop.set()
        return web.json_response({"stopping": True})

    app = web.Application()
    app.add_routes([web.get("/", page), web.get("/status", status),
                    web.post("/command", command), web.post("/stop", shutdown)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    http_port = site._server.sockets[0].getsockname()[1]
    print(json.dumps({"wsPort": port, "url": f"http://127.0.0.1:{http_port}"}), flush=True)
    try:
        await asyncio.wait_for(stop.wait(), timeout=180)
    finally:
        await bridge.stop()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
