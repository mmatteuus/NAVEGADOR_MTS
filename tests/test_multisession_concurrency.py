"""Suíte de Testes Concorrentes Multissessão (M-E2E).
Valida múltiplos agentes operando de forma concorrente via WebSocket Bridge.
"""
from __future__ import annotations
import asyncio, json, pytest
from websockets.asyncio.client import connect
from src.mcp.ws_bridge import WebSocketBridge


async def _handshake_ext(ws, version: str = "2.2.1") -> dict:
    """Helper para handshake inicial com a extensão."""
    await ws.send(json.dumps({"type": "client_hello", "payload": {"version": version}}))
    return json.loads(await ws.recv())


def _setup_bridge(port: int) -> WebSocketBridge:
    """Instancia o bridge garantindo tipo set para sockets de agentes."""
    bridge = WebSocketBridge(host="127.0.0.1", port=port)
    if isinstance(getattr(bridge.registry, "_agent_sockets", None), list):
        bridge.registry._agent_sockets = set(bridge.registry._agent_sockets)
    return bridge


def test_concurrent_multisession_gather(dynamic_port: int) -> None:
    """Valida 2 agentes enviando comandos concorrentes via asyncio.gather sem colisão."""
    bridge = _setup_bridge(dynamic_port)

    async def _run() -> None:
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        async with connect(uri) as ext_ws:
            await _handshake_ext(ext_ws)

            async def mock_ext() -> None:
                for _ in range(6):
                    cmd = json.loads(await ext_ws.recv())
                    sess = cmd["payload"].get("sessionId", "unknown")
                    resp = {"type": "browser_response", "id": cmd["id"],
                            "payload": {"requestId": cmd["id"], "result": {"ok": True, "sessionId": sess}}}
                    await ext_ws.send(json.dumps(resp))

            ext_t = asyncio.create_task(mock_ext())

            async def run_agent(sess_id: str, count: int) -> list[dict]:
                res = []
                async with connect(uri) as a_ws:
                    for i in range(count):
                        msg = {"type": "agent_action", "id": f"{sess_id}_{i}", "sessionId": sess_id,
                               "action": "browser_navigate", "params": {"sessionId": sess_id, "url": f"https://site.test/{i}"}}
                        await a_ws.send(json.dumps(msg))
                        res.append(json.loads(await a_ws.recv()))
                return res

            res_a, res_b = await asyncio.gather(run_agent("sess_a", 3), run_agent("sess_b", 3))
            await ext_t
            assert len(res_a) == 3 and len(res_b) == 3, "Cada agente deve receber 3 respostas"
            assert all(r["result"]["sessionId"] == "sess_a" for r in res_a), "Respostas A segregadas"
            assert all(r["result"]["sessionId"] == "sess_b" for r in res_b), "Respostas B segregadas"

        await bridge.stop()

    asyncio.run(_run())


def test_multisession_disconnect_resilience(dynamic_port: int) -> None:
    """Valida que queda intempestiva do Agente A não afeta a sessão do Agente B."""
    bridge = _setup_bridge(dynamic_port)

    async def _run() -> None:
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        async with connect(uri) as ext_ws:
            await _handshake_ext(ext_ws)

            async def ext_echo() -> None:
                while True:
                    try:
                        c = json.loads(await ext_ws.recv())
                        await ext_ws.send(json.dumps({"type": "browser_response", "id": c["id"],
                                                      "payload": {"requestId": c["id"], "result": {"ok": True}}}))
                    except Exception:
                        break

            t = asyncio.create_task(ext_echo())
            async with connect(uri) as a_ws:
                await a_ws.send(json.dumps({"type": "agent_action", "id": "a1", "action": "browser_navigate",
                                            "params": {"url": "https://a.com"}}))
                assert json.loads(await a_ws.recv())["success"] is True

            async with connect(uri) as b_ws:
                for j in range(2):
                    await b_ws.send(json.dumps({"type": "agent_action", "id": f"b{j}", "action": "browser_navigate",
                                                "params": {"url": "https://b.com"}}))
                    r = json.loads(await b_ws.recv())
                    assert r["success"] is True and r["id"] == f"b{j}"
            t.cancel()

        await bridge.stop()

    asyncio.run(_run())


def test_multisession_isolated_error_handling(dynamic_port: int) -> None:
    """Valida que falha em uma sessão é contida sem vazar para sessões paralelas."""
    bridge = _setup_bridge(dynamic_port)

    async def _run() -> None:
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        async with connect(uri) as ext_ws:
            await _handshake_ext(ext_ws)

            async def ext_router() -> None:
                for _ in range(2):
                    c = json.loads(await ext_ws.recv())
                    err = "Aba inacessível" if c["payload"].get("sessionId") == "fail_sess" else None
                    p = {"requestId": c["id"], "error": err} if err else {"requestId": c["id"], "result": {"status": "ok"}}
                    await ext_ws.send(json.dumps({"type": "browser_response", "id": c["id"], "payload": p}))

            t = asyncio.create_task(ext_router())

            async def call(sid: str) -> dict:
                async with connect(uri) as ws:
                    await ws.send(json.dumps({"type": "agent_action", "id": f"req_{sid}", "sessionId": sid,
                                              "action": "browser_navigate", "params": {"sessionId": sid}}))
                    return json.loads(await ws.recv())

            res_fail, res_ok = await asyncio.gather(call("fail_sess"), call("ok_sess"))
            await t
            assert res_fail["success"] is False and "Aba inacessível" in res_fail["error"]
            assert res_ok["success"] is True and res_ok["result"] == {"status": "ok"}

        await bridge.stop()

    asyncio.run(_run())
