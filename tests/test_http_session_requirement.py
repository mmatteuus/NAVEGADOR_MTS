"""Chamadas HTTP não compartilham a identidade stdio do processo servidor."""
from __future__ import annotations

import asyncio
from aiohttp import ClientSession
from src.mcp.http_server import MCPHTTPServer
from src.mcp.server import MCPServer
from src.mcp.session_manager import session_manager


def test_http_requires_initialized_session_before_tools(dynamic_port):
    """Cabeçalho ausente ou desconhecido nunca executa uma ferramenta."""
    async def scenario():
        session_manager.clear()
        server = MCPHTTPServer(MCPServer(), dynamic_port)
        await server.start()
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": "computer_get_status", "arguments": {}}}
        try:
            async with ClientSession() as client:
                url = f"http://127.0.0.1:{dynamic_port}/mcp"
                async with client.post(url, json=request) as response:
                    assert response.status == 400
                    assert "SESSION_REQUIRED" in await response.text()
                async with client.post(url, json=request, headers={"Mcp-Session-Id": "unknown"}) as response:
                    assert response.status == 404
                async with client.post(url, json={"jsonrpc": "2.0", "id": 2,
                    "method": "initialize", "params": {"clientInfo": {"name": "chat"}}}) as response:
                    sid = response.headers["Mcp-Session-Id"]
                async with client.post(url, json=request, headers={"Mcp-Session-Id": sid}) as response:
                    assert response.status == 200
                    assert not (await response.json())["result"]["isError"]
        finally:
            await server.stop()
            session_manager.clear()
    asyncio.run(scenario())
