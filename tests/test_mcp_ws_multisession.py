"""Suíte de Testes para Concorrência Multissessão MCP e WebSocket.

Valida conexões simultâneas de múltiplos agentes, locks granulares por sessão,
segregação de abas no router e propagação de cabeçalhos de sessão no servidor HTTP.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from aiohttp import ClientSession
from websockets.asyncio.client import connect
from src.mcp import MCPServer, MCPToolRouter, WebSocketBridge
from src.mcp.http_server import MCPHTTPServer
from src.mcp.session_manager import session_manager


def test_concurrent_multiagent_websocket_connections(dynamic_port: int) -> None:
    """Valida múltiplos agentes conectados simultaneamente sem colisão de sockets."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        async with connect(uri) as ext_ws:
            await ext_ws.send(json.dumps({"type": "client_hello", "payload": {"v": "2.0"}}))
            assert json.loads(await ext_ws.recv())["type"] == "server_hello"

            async def mock_extension_loop():
                for _ in range(3):
                    raw = await ext_ws.recv()
                    cmd = json.loads(raw)
                    reply = {"type": "browser_response", "id": cmd["id"],
                             "payload": {"requestId": cmd["id"], "result": {"nav": cmd["payload"]["url"]}}}
                    await ext_ws.send(json.dumps(reply))

            ext_task = asyncio.create_task(mock_extension_loop())

            async def agent_worker(agent_idx: int):
                async with connect(uri) as agent_ws:
                    msg = {"type": "agent_action", "id": f"cmd_{agent_idx}", "action": "browser_navigate",
                           "params": {"url": f"https://site-{agent_idx}.com"}, "sessionId": f"sess_{agent_idx}"}
                    await agent_ws.send(json.dumps(msg))
                    res = json.loads(await agent_ws.recv())
                    assert res["success"] is True and res["result"]["nav"] == f"https://site-{agent_idx}.com"

            await asyncio.gather(*(agent_worker(i) for i in range(3)))
            await ext_task
        await bridge.stop()

    asyncio.run(_run())


def test_granular_session_locking_concurrency() -> None:
    """Valida que sessões distintas operam em paralelo e a mesma sessão é serializada."""
    async def _run():
        session_manager.clear()
        sess_a = await session_manager.get_or_create_session("sess_A")
        sess_b = await session_manager.get_or_create_session("sess_B")
        exec_order = []

        async def job(sess, label: str, delay: float):
            async with sess.lock:
                exec_order.append(f"start_{label}")
                await asyncio.sleep(delay)
                exec_order.append(f"end_{label}")

        # Sessões distintas executam intercaladas (concorrentes)
        await asyncio.gather(job(sess_a, "A1", 0.05), job(sess_b, "B1", 0.05))
        assert "start_A1" in exec_order and "start_B1" in exec_order

        # Mesma sessão executa estritamente serializada
        exec_order.clear()
        await asyncio.gather(job(sess_a, "A1", 0.05), job(sess_a, "A2", 0.01))
        assert exec_order == ["start_A1", "end_A1", "start_A2", "end_A2"]

    asyncio.run(_run())


def test_tab_isolation_and_ownership_in_router() -> None:
    """Valida recusa de acesso a abas que pertencem a outra sessão de agente."""
    async def _run():
        session_manager.clear()
        session_manager.assign_tab_to_session("sess_alpha", 101)

        bridge = WebSocketBridge(port=9200)
        bridge._active_socket = object()
        bridge.send_action = lambda a, p, **kw: asyncio.sleep(0, result={"ok": True})
        router = MCPToolRouter(ws_bridge=bridge)

        # Sessão não autorizada deve ser rejeitada
        res_denied = await router.dispatch(
            "browser_navigate", {"url": "https://sec.com", "tabId": 101, "sessionId": "sess_beta"}, session_id="sess_beta"
        )
        assert res_denied["isError"] is True
        assert "Acesso recusado" in res_denied["content"][0]["text"]

        # Sessão proprietária deve ter acesso concedido
        res_allowed = await router.dispatch(
            "browser_navigate", {"url": "https://sec.com", "tabId": 101, "sessionId": "sess_alpha"}, session_id="sess_alpha"
        )
        assert res_allowed["isError"] is False

    asyncio.run(_run())


def test_http_server_session_header_propagation(dynamic_port: int) -> None:
    """Valida que cabeçalhos Mcp-Session-Id são capturados e devolvidos no HTTP Server."""
    async def _run():
        server = MCPServer()
        endpoint = MCPHTTPServer(server, dynamic_port)
        await endpoint.start()
        try:
            async with ClientSession() as client:
                url = f"http://127.0.0.1:{dynamic_port}/mcp"
                headers = {"Mcp-Session-Id": "sess_test_http_123"}
                payload = {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}
                async with client.post(url, json=payload, headers=headers) as resp:
                    assert resp.status == 200
                    assert resp.headers.get("Mcp-Session-Id") == "sess_test_http_123"
        finally:
            await endpoint.stop()

    asyncio.run(_run())
