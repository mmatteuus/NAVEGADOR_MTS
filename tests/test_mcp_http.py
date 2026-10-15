"""Teste do transporte HTTP MCP com ponte local e sem abrir portas externas."""
import asyncio
import socket
from aiohttp import ClientSession
from src.mcp.http_server import MCPHTTPServer
from src.mcp.server import MCPServer


def test_http_mcp_initialize_and_methods():
    async def scenario():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        endpoint = MCPHTTPServer(MCPServer(), port)
        await endpoint.start()
        try:
            async with ClientSession() as client:
                url = f"http://127.0.0.1:{port}/mcp"
                async with client.post(url, json={"jsonrpc": "2.0", "id": 1,
                    "method": "initialize", "params": {}}) as r:
                    assert r.status == 200
                    body = await r.json()
                    assert body["result"]["serverInfo"]["name"] == "browser-mcp-mts"
                async with client.post(url, json={"jsonrpc": "2.0", "id": 2,
                    "method": "tools/list", "params": {}}) as r:
                    assert len((await r.json())["result"]["tools"]) >= 14
                async with client.get(url) as r:
                    assert r.status == 405
                async with client.post(url, data="invalid") as r:
                    assert r.status == 415
                async with client.post(url, json={"jsonrpc": "2.0",
                    "method": "notifications/initialized"}) as r:
                    assert r.status == 202
        finally:
            await endpoint.stop()
    asyncio.run(scenario())
