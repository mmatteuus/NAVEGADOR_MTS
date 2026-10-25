"""E2E local: POST /mcp -> WebSocket -> extensão simulada -> resposta."""
from __future__ import annotations

import asyncio
import json
import socket

from aiohttp import ClientSession
from websockets.asyncio.client import connect

from src.mcp.http_server import MCPHTTPServer
from src.mcp.server import MCPServer
from src.mcp.ws_bridge import WebSocketBridge


def test_http_to_websocket_end_to_end(dynamic_port):
    """Navegação HTTP chega à extensão simulada sem portas públicas."""
    async def run():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            http_port = sock.getsockname()[1]
        bridge = WebSocketBridge(port=dynamic_port)
        server = MCPHTTPServer(MCPServer(ws_bridge=bridge), http_port)
        await bridge.start()
        await server.start()
        try:
            async with connect(f"ws://127.0.0.1:{dynamic_port}") as extension:
                await extension.send(json.dumps({"type": "client_hello"}))
                assert json.loads(await extension.recv())["type"] == "server_hello"
                async with ClientSession() as client:
                    url = f"http://127.0.0.1:{http_port}/mcp"
                    async with client.post(url, json={"jsonrpc": "2.0", "id": 1,
                        "method": "initialize", "params": {}}) as initialized:
                        sid = initialized.headers["Mcp-Session-Id"]
                    assert json.loads(await asyncio.wait_for(extension.recv(), 3))["type"] == "agents_changed"
                    task = asyncio.create_task(client.post(url, headers={"Mcp-Session-Id": sid}, json={
                        "jsonrpc": "2.0", "id": 7, "method": "tools/call",
                        "params": {"name": "browser_navigate",
                                   "arguments": {"url": "https://example.com"}}}))
                    instruction = json.loads(await asyncio.wait_for(extension.recv(), 3))
                    assert instruction["action"] == "browser_navigate"
                    await extension.send(json.dumps({"type": "browser_response",
                        "id": instruction["id"], "payload": {
                            "requestId": instruction["id"], "result": {"navigated": True}}}))
                    response = await asyncio.wait_for(task, 3)
                    async with response:
                        body = await response.json()
                        assert response.status == 200
                        assert body["result"]["isError"] is False
                        assert json.loads(body["result"]["content"][0]["text"])["navigated"]
        finally:
            await server.stop()
            await bridge.stop()
    asyncio.run(run())
