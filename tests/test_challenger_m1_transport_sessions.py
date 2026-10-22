"""Suíte de Testes Adversariais Empíricos: Transporte e Sessões MCP (Challenger v4.1).

Cobre: emissão automática de Mcp-Session-Id via HTTP, defesa anti-forja,
concorrência de processos Stdio e compatibilidade com o fluxo legado.
"""
from __future__ import annotations
import asyncio
import socket
from aiohttp import ClientSession
from src.mcp import MCPServer, MCPToolRouter
from src.mcp.http_server import MCPHTTPServer
from src.mcp.session_manager import session_manager

class _MockBridge:
    def __init__(self):
        self.is_connected = True
        self.tab_seq = 500

    async def send_action(self, act: str, params: dict, **kw):
        if act == "browser_manage_tabs" and params.get("action") == "new":
            self.tab_seq += 1
            return {"success": True, "tabId": self.tab_seq}
        return {"success": True, "data": {"act": act, "tabId": params.get("tabId")}}

def _get_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_adversarial_http_streamable_automatic_session_emission():
    """Dois clientes HTTP no handshake initialize recebem sessões distintas e operam isolados."""
    async def _run():
        session_manager.clear()
        port = _get_free_port()
        srv = MCPServer(ws_bridge=_MockBridge())
        http_srv = MCPHTTPServer(srv, port)
        await http_srv.start()
        try:
            async with ClientSession() as cli:
                url = f"http://127.0.0.1:{port}/mcp"
                init_p = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
                async with cli.post(url, json=init_p) as r1:
                    assert r1.status == 200
                    sid1 = r1.headers.get("Mcp-Session-Id")
                    assert sid1 and sid1.startswith("sess_")
                async with cli.post(url, json=init_p) as r2:
                    assert r2.status == 200
                    sid2 = r2.headers.get("Mcp-Session-Id")
                    assert sid2 and sid2.startswith("sess_")
                assert sid1 != sid2, f"Colisão detectada: {sid1} == {sid2}"
                new_tab_p = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                             "params": {"name": "browser_manage_tabs", "arguments": {"action": "new", "url": "https://a.com"}}}
                async with cli.post(url, json=new_tab_p, headers={"Mcp-Session-Id": sid1}) as r:
                    assert (await r.json())["result"]["isError"] is False
                assert session_manager.get_session(sid1).has_tab(501) is True
                nav_p = {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                         "params": {"name": "browser_navigate", "arguments": {"tabId": 501, "url": "https://evil.com"}}}
                async with cli.post(url, json=nav_p, headers={"Mcp-Session-Id": sid2}) as r:
                    res2 = (await r.json())["result"]
                    assert res2["isError"] is True and "Acesso recusado" in res2["content"][0]["text"]
        finally:
            await http_srv.stop()
            session_manager.clear()
    asyncio.run(_run())


def test_adversarial_active_session_forgery_denial():
    """Agente B tenta injetar sessionId de Agente A nos argumentos e é sumariamente negado."""
    async def _run():
        session_manager.clear()
        port = _get_free_port()
        bridge = _MockBridge()
        srv = MCPServer(ws_bridge=bridge)
        http_srv = MCPHTTPServer(srv, port)
        await http_srv.start()
        try:
            session_manager.assign_tab_to_session("sess_A", 101)
            async with ClientSession() as cli:
                url = f"http://127.0.0.1:{port}/mcp"
                forge_p = {"jsonrpc": "2.0", "id": 10, "method": "tools/call",
                           "params": {"name": "browser_navigate", "arguments": {"tabId": 101, "sessionId": "sess_A"}}}
                async with cli.post(url, json=forge_p, headers={"Mcp-Session-Id": "sess_B"}) as r:
                    res = (await r.json())["result"]
                    assert res["isError"] is True and "forja" in res["content"][0]["text"].lower()
                forge_snake = {"jsonrpc": "2.0", "id": 11, "method": "tools/call",
                               "params": {"name": "browser_navigate", "arguments": {"tabId": 101, "session_id": "sess_A"}}}
                async with cli.post(url, json=forge_snake, headers={"Mcp-Session-Id": "sess_B"}) as r:
                    res2 = (await r.json())["result"]
                    assert res2["isError"] is True and "forja" in res2["content"][0]["text"].lower()
            router = MCPToolRouter(ws_bridge=bridge)
            res3 = await router.dispatch("browser_navigate", {"tabId": 101, "sessionId": "sess_A"}, session_id="sess_B")
            assert res3["isError"] is True and "forja" in res3["content"][0]["text"].lower()
        finally:
            await http_srv.stop()
            session_manager.clear()
    asyncio.run(_run())


def test_adversarial_multiple_stdio_processes_concurrency():
    """Múltiplos processos stdio geram identificadores distintos e operam sem colisão."""
    async def _run():
        session_manager.clear()
        try:
            bridge = _MockBridge()
            srv1, srv2 = MCPServer(ws_bridge=bridge), MCPServer(ws_bridge=bridge)
            assert srv1.process_session_id.startswith("stdio_") and srv2.process_session_id.startswith("stdio_")
            assert srv1.process_session_id != srv2.process_session_id
            req1 = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "browser_manage_tabs", "arguments": {"action": "new", "url": "https://p1.org"}}}
            req2 = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "browser_manage_tabs", "arguments": {"action": "new", "url": "https://p2.org"}}}
            res1, res2 = await asyncio.gather(srv1.handle_jsonrpc(req1), srv2.handle_jsonrpc(req2))
            assert res1["result"]["isError"] is False and res2["result"]["isError"] is False
            nav_req2 = {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                        "params": {"name": "browser_navigate", "arguments": {"tabId": 501, "url": "https://hack.org"}}}
            res_denied = await srv2.handle_jsonrpc(nav_req2)
            assert res_denied["result"]["isError"] is True and "Acesso recusado" in res_denied["result"]["content"][0]["text"]
        finally:
            session_manager.clear()
    asyncio.run(_run())


def test_adversarial_legacy_request_without_session_fallback():
    """Requisição legada sem cabeçalho nem sessionId opera sobre abas gerais com sucesso."""
    async def _run():
        session_manager.clear()
        port = _get_free_port()
        srv = MCPServer(ws_bridge=_MockBridge())
        http_srv = MCPHTTPServer(srv, port)
        await http_srv.start()
        try:
            async with ClientSession() as cli:
                url = f"http://127.0.0.1:{port}/mcp"
                req = {"jsonrpc": "2.0", "id": 50, "method": "tools/call",
                       "params": {"name": "browser_navigate", "arguments": {"tabId": 9999, "url": "https://legacy.org"}}}
                async with cli.post(url, json=req) as r:
                    assert r.status == 200 and "Mcp-Session-Id" not in r.headers
                    assert (await r.json())["result"]["isError"] is False
                session_manager.assign_tab_to_session("sess_privada", 8888)
                req_priv = {"jsonrpc": "2.0", "id": 51, "method": "tools/call",
                            "params": {"name": "browser_navigate", "arguments": {"tabId": 8888, "url": "https://bypass.org"}}}
                async with cli.post(url, json=req_priv) as r:
                    res_priv = (await r.json())["result"]
                    assert res_priv["isError"] is True and "Acesso recusado" in res_priv["content"][0]["text"]
        finally:
            await http_srv.stop()
            session_manager.clear()
    asyncio.run(_run())
