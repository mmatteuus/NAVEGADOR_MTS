"""Teste de integração do túnel com o servidor HTTP MCP."""
import asyncio
import socket
from aiohttp import ClientSession
from src.mcp.http_server import MCPHTTPServer
from src.mcp.server import MCPServer
from src.mcp.ws_bridge import WebSocketBridge


def test_tunnel_http_connection():
    """Testa que o túnel consegue se conectar através do servidor HTTP MCP."""
    async def _run():
        # Configurar servidor local
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]

        bridge = WebSocketBridge(port=port + 1)
        server = MCPHTTPServer(MCPServer(ws_bridge=bridge), port)
        await bridge.start()
        await server.start()

        try:
            # Simular cliente do túnel (ChatGPT)
            async with ClientSession() as client:
                # Requisição do túnel - Host será diferente do localhost
                url = f"http://127.0.0.1:{port}/mcp"
                async with client.post(url, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {}
                }) as r:
                    assert r.status == 200, f"Falha na requisição do túnel: {r.status}"
                    body = await r.json()
                    assert body["result"]["serverInfo"]["name"] == "browser-mcp-mts"

                # Testar tools/list
                async with client.post(url, json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }) as r:
                    assert r.status == 200, f"Falha no tools/list do túnel: {r.status}"
                    body = await r.json()
                    assert "tools" in body["result"]

        finally:
            await server.stop()
            await bridge.stop()

    asyncio.run(_run())


def test_tunnel_host_validation():
    """Testa que o servidor aceita Host do túnel quando Origin é válida."""
    async def _run():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]

        bridge = WebSocketBridge(port=port + 1)
        server = MCPHTTPServer(MCPServer(ws_bridge=bridge), port)
        await bridge.start()
        await server.start()

        try:
            async with ClientSession() as client:
                # Requisição com Host não padrão (túnel)
                url = f"http://127.0.0.1:{port}/mcp"

                # Host inválido, mas Origin válida (simula túnel)
                async with client.post(url, headers={
                    "Host": "external-domain.com",
                    "Origin": f"http://localhost:{port}"
                }, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {}
                }) as r:
                    assert r.status == 200, f"Requisição com Host inválido deve passar: {r.status}"

                # Host inválido e Origin inválida (deve falhar)
                async with client.post(url, headers={
                    "Host": "external-domain.com",
                    "Origin": "https://external-domain.com"
                }, json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "initialize",
                    "params": {}
                }) as r:
                    assert r.status == 403, f"Requisição com Host e Origin inválidos deve falhar: {r.status}"

        finally:
            await server.stop()
            await bridge.stop()

    asyncio.run(_run())