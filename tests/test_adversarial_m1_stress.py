"""Testes de estresse adversarial da camada MCP e WebSocket multissessão.

Testa rajadas de 50 agentes simultâneos, desconexão intempestiva da extensão,
cancelamentos abruptos de clientes de IA e concorrência no SessionManager.
"""
from __future__ import annotations
import asyncio, json, pytest
from websockets.asyncio.client import connect
from src.mcp import WebSocketBridge
from src.mcp.session_manager import session_manager


def test_stress_50_concurrent_agents_burst(dynamic_port: int) -> None:
    """Dispara rajada de 50 agentes simultâneos em sockets distintos validando zero perda."""
    bridge, num_agents = WebSocketBridge(host="127.0.0.1", port=dynamic_port), 50

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        async with connect(uri) as ext_ws:
            await ext_ws.send(json.dumps({"type": "client_hello", "payload": {}}))
            assert json.loads(await ext_ws.recv())["type"] == "server_hello"

            async def mock_ext():
                for _ in range(num_agents):
                    cmd = json.loads(await ext_ws.recv())
                    reply = {"type": "browser_response", "id": cmd["id"],
                             "payload": {"requestId": cmd["id"], "result": {"echo": cmd["action"], "sid": cmd.get("sessionId")}}}
                    await ext_ws.send(json.dumps(reply))

            ext_task = asyncio.create_task(mock_ext())

            async def agent_task(i: int):
                async with connect(uri) as ag_ws:
                    msg = {"type": "agent_action", "id": f"burst_{i}", "action": "browser_click",
                           "params": {"selector": f"#btn_{i}"}, "sessionId": f"sess_burst_{i}"}
                    await ag_ws.send(json.dumps(msg))
                    resp = json.loads(await ag_ws.recv())
                    assert resp["success"] is True
                    assert resp["result"]["echo"] == "browser_click"
                    assert resp["result"]["sid"] == f"sess_burst_{i}"

            await asyncio.gather(*(agent_task(i) for i in range(num_agents)))
            await ext_task
            assert len(bridge._pending_requests) == 0
        await bridge.stop()

    asyncio.run(_run())


def test_stress_abrupt_extension_disconnect_inflight(dynamic_port: int) -> None:
    """Testa queda intempestiva do socket da extensão com requisições em voo."""
    bridge, burst_size = WebSocketBridge(host="127.0.0.1", port=dynamic_port), 20

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        ext_ws = await connect(uri)
        await ext_ws.send(json.dumps({"type": "client_hello", "payload": {}}))
        await ext_ws.recv()
        await ext_ws.close()
        await asyncio.sleep(0.05)

        async def failing_agent(i: int):
            async with connect(uri) as ag_ws:
                msg = {"type": "agent_action", "id": f"disc_{i}", "action": "browser_click", "sessionId": f"s_{i}"}
                await ag_ws.send(json.dumps(msg))
                resp = json.loads(await ag_ws.recv())
                assert resp["success"] is False
                assert "não conectada" in resp["error"]

        await asyncio.gather(*(failing_agent(i) for i in range(burst_size)))
        assert bridge.is_connected is False

        async with connect(uri) as new_ext:
            await new_ext.send(json.dumps({"type": "client_hello", "payload": {}}))
            await new_ext.recv()
            assert bridge.is_connected is True
        await bridge.stop()

    asyncio.run(_run())


def test_stress_abrupt_agent_disconnect_during_dispatch(dynamic_port: int) -> None:
    """Testa desconexão abrupta de agentes sem corrupção de estado ou travamento."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        async with connect(uri) as ext_ws:
            await ext_ws.send(json.dumps({"type": "client_hello", "payload": {}}))
            await ext_ws.recv()

            async def drop_agent(i: int):
                ag_ws = await connect(uri)
                msg = {"type": "agent_action", "id": f"drop_{i}", "action": "browser_click", "sessionId": f"s_{i}"}
                await ag_ws.send(json.dumps(msg))
                await ag_ws.close()

            await asyncio.gather(*(drop_agent(i) for i in range(15)))
            for _ in range(15):
                try:
                    raw = await asyncio.wait_for(ext_ws.recv(), timeout=0.2)
                    cmd = json.loads(raw)
                    reply = {"type": "browser_response", "id": cmd["id"], "payload": {"requestId": cmd["id"], "result": {}}}
                    await ext_ws.send(json.dumps(reply))
                except asyncio.TimeoutError: break
            assert bridge.is_connected is True
        await bridge.stop()

    asyncio.run(_run())


def test_stress_session_manager_concurrency() -> None:
    """Testa concorrência extrema de 100 tarefas simultâneas no SessionManager."""
    async def _run():
        session_manager.clear()

        async def worker(idx: int):
            sid = f"sess_stress_{idx % 10}"
            sess = await session_manager.get_or_create_session(sid, agent_id=f"agent_{idx}")
            assert sess.session_id == sid
            session_manager.assign_tab_to_session(sid, 1000 + idx)
            assert session_manager.validate_tab_access(sid, 1000 + idx) is True
            assert session_manager.validate_tab_access(f"other_{sid}", 1000 + idx) is False
            assert sid in session_manager.list_active_sessions()
            if idx % 5 == 0: await session_manager.close_session(sid)

        await asyncio.gather(*(worker(i) for i in range(100)))

    asyncio.run(_run())
