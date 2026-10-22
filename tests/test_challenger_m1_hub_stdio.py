"""Suíte de Testes Adversariais Empíricos: Hub WebSocket e Concorrência Stdio (Challenger v4.1).

Valida empiricamente que múltiplos processos stdio encaminham chamadas
ao Hub WebSocket com sessões stdio_<pid>_<uuid> estáveis, distintas e anti-forja.
"""
from __future__ import annotations
import asyncio
import json
import socket
from websockets.asyncio.client import connect
from src.mcp.ws_bridge import WebSocketBridge
from src.mcp.server import MCPServer
from src.mcp.session_manager import session_manager


def _get_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_adversarial_two_stdio_processes_forwarding_to_hub():
    """Dois processos stdio encaminham chamadas ao Hub simultaneamente com sessões distintas."""
    async def _run():
        session_manager.clear()
        port = _get_free_port()
        hub = WebSocketBridge(host="127.0.0.1", port=port)
        await hub.start()

        async def run_ext_responder():
            async with connect(f"ws://127.0.0.1:{port}") as ext_ws:
                await ext_ws.send(json.dumps({"type": "client_hello", "payload": {"name": "Ext"}}))
                await ext_ws.recv()
                while True:
                    msg_raw = await ext_ws.recv()
                    msg = json.loads(msg_raw)
                    if msg.get("type") == "execute_action":
                        reply = {
                            "type": "browser_response",
                            "payload": {
                                "requestId": msg["id"],
                                "result": {"echo_sid": msg.get("sessionId"), "action": msg.get("action")}
                            }
                        }
                        await ext_ws.send(json.dumps(reply))

        ext_task = asyncio.create_task(run_ext_responder())
        await asyncio.sleep(0.05)

        try:
            srv1 = MCPServer(host="127.0.0.1", ws_port=port)
            await srv1.start(start_ws=True)
            srv2 = MCPServer(host="127.0.0.1", ws_port=port)
            await srv2.start(start_ws=True)

            assert srv1._use_active_hub is True and srv2._use_active_hub is True
            assert srv1.process_session_id.startswith("stdio_")
            assert srv2.process_session_id.startswith("stdio_")
            assert srv1.process_session_id != srv2.process_session_id

            req1 = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "browser_navigate", "arguments": {"url": "https://p1.org"}}}
            req2 = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "browser_navigate", "arguments": {"url": "https://p2.org"}}}

            res1, res2 = await asyncio.gather(srv1.handle_jsonrpc(req1), srv2.handle_jsonrpc(req2))
            assert res1["result"]["isError"] is False and res2["result"]["isError"] is False

            data1 = json.loads(res1["result"]["content"][0]["text"])
            data2 = json.loads(res2["result"]["content"][0]["text"])
            assert data1["echo_sid"] == srv1.process_session_id
            assert data2["echo_sid"] == srv2.process_session_id
        finally:
            ext_task.cancel()
            await hub.stop()
            session_manager.clear()

    asyncio.run(_run())


def test_adversarial_stdio_to_hub_forgery_rejection():
    """Tentativa de injetar sessionId de outro processo stdio em chamada ao hub é bloqueada."""
    async def _run():
        session_manager.clear()
        port = _get_free_port()
        hub = WebSocketBridge(host="127.0.0.1", port=port)
        await hub.start()

        async def run_dummy_ext():
            async with connect(f"ws://127.0.0.1:{port}") as ext_ws:
                await ext_ws.send(json.dumps({"type": "client_hello", "payload": {}}))
                await ext_ws.recv()
                while True:
                    await ext_ws.recv()

        ext_task = asyncio.create_task(run_dummy_ext())
        await asyncio.sleep(0.05)

        try:
            srv1 = MCPServer(host="127.0.0.1", ws_port=port)
            await srv1.start(start_ws=True)
            srv2 = MCPServer(host="127.0.0.1", ws_port=port)
            await srv2.start(start_ws=True)

            forge_req = {
                "jsonrpc": "2.0", "id": 99, "method": "tools/call",
                "params": {"name": "browser_navigate", "arguments": {"url": "https://evil.org", "sessionId": srv1.process_session_id}}
            }
            res = await srv2.handle_jsonrpc(forge_req)
            assert res["result"]["isError"] is True
            assert "forja" in res["result"]["content"][0]["text"].lower()
        finally:
            ext_task.cancel()
            await hub.stop()
            session_manager.clear()

    asyncio.run(_run())
