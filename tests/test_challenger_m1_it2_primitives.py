"""Suíte de Desafio: Primitivos JSON e Resiliência — Marco 1 Iteração 2 (Challenger 1).

Testa empiricamente resiliência a ataques com tipos primitivos JSON
(int, float, bool, list, null) e payloads malformados contra router,
session_manager e ws_action_dispatcher.
"""
from __future__ import annotations
import asyncio
import json
import pytest
from websockets.asyncio.client import connect
from src.mcp import MCPToolRouter, WebSocketBridge
from src.mcp.session_manager import session_manager
from src.mcp.ws_action_dispatcher import dispatch_agent_action


def test_adversarial_raw_primitives_ws_envelope(dynamic_port: int) -> None:
    """Desafio: WebSocket resiste a rajada de primitivos puros sem encerrar o canal."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        primitives = ["42", "3.14159", "true", "false", "null", "[]", "\"raw_string\"", "[1, 2, {\"a\": 1}]"]
        async with connect(uri) as ws:
            for prim in primitives:
                await ws.send(prim)

            # Canal deve permanecer aberto e responder a ping legítimo
            await ws.send(json.dumps({"type": "ping", "ts": 12345}))
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            res = json.loads(raw)
            assert res.get("type") == "pong"
            assert res.get("ts") == 12345

        await bridge.stop()

    asyncio.run(_run())


def test_adversarial_agent_action_primitive_fields() -> None:
    """Desafio: agent_action com action, params ou tabId como tipos primitivos inválidos."""
    class MockWS:
        def __init__(self):
            self.responses = []
        async def send(self, msg: str):
            self.responses.append(json.loads(msg))

    async def _run():
        session_manager.clear()
        try:
            mock_ws = MockWS()
            calls = []
            async def mock_send(act, params, **kw):
                calls.append((act, params))
                return {"success": True}

            test_cases = [
                {"type": "agent_action", "id": "t1", "action": 12345, "params": {}},
                {"type": "agent_action", "id": "t2", "action": None, "params": {}},
                {"type": "agent_action", "id": "t3", "action": "browser_click", "params": 42},
                {"type": "agent_action", "id": "t4", "action": "browser_click", "params": True},
                {"type": "agent_action", "id": "t5", "action": "browser_click", "params": [1, 2, 3]},
                {"type": "agent_action", "id": "t6", "action": "browser_click", "params": "string_param"},
                {"type": "agent_action", "id": "t7", "action": "browser_click", "sessionId": 9999, "params": {}},
            ]

            for case in test_cases:
                await dispatch_agent_action(case, mock_ws, mock_send)

            assert len(calls) == 0, "Nenhuma chamada corrompida deve atingir a extensão"
            assert len(mock_ws.responses) == len(test_cases)
            for resp in mock_ws.responses:
                assert resp.get("success") is False
                assert "error" in resp or "Ação desconhecida" in str(resp)
        finally:
            session_manager.clear()

    asyncio.run(_run())


def test_adversarial_router_malformed_arguments() -> None:
    """Desafio: router.dispatch com argumentos contendo primitivos corrompidos ou sessionId numérico."""
    async def _run():
        session_manager.clear()
        try:
            session_manager.assign_tab_to_session("sess_real", 999)
            bridge = WebSocketBridge(port=9311)
            bridge._active_socket = object()
            bridge.send_action = lambda a, p, **kw: asyncio.sleep(0, result={"success": True})
            router = MCPToolRouter(ws_bridge=bridge)

            # 1. sessionId numérico (não-string) em vez de crashar, responde com isError
            res_sid = await router.dispatch("browser_navigate", {"url": "https://test.com", "sessionId": 123, "tabId": 999})
            assert isinstance(res_sid, dict)
            assert res_sid["isError"] is True

            # 2. tabId com tipos primitivos bizarros (float, lista, dict, string inválida)
            bizarre_tab_ids = ["abc", [1, 2], {"nested": 1}, None]
            for bad_tid in bizarre_tab_ids:
                res = await router.dispatch("browser_navigate", {"url": "https://test.com", "tabId": bad_tid})
                assert isinstance(res, dict)
                assert "isError" in res

            # 3. Ferramenta desconhecida
            res_unknown = await router.dispatch("unknown_tool_xyz", {"foo": "bar"})
            assert res_unknown["isError"] is True
            assert "Ferramenta desconhecida" in res_unknown["content"][0]["text"]
        finally:
            session_manager.clear()

    asyncio.run(_run())


def test_adversarial_session_manager_extract_and_validate_edge_cases() -> None:
    """Desafio: session_manager sob ataques de tipos malformados em tab_id e responses."""
    session_manager.clear()
    try:
        # validate_tab_access com tipos primitivos bizarros
        assert session_manager.validate_tab_access(None, "not_an_int") is False
        assert session_manager.validate_tab_access("sess1", [101]) is False
        assert session_manager.validate_tab_access("sess1", {"id": 101}) is False
        assert session_manager.validate_tab_access("sess1", None) is False

        # extract_tab_id com envelopes variados e corrompidos
        assert session_manager.extract_tab_id(None) is None
        assert session_manager.extract_tab_id("string") is None
        assert session_manager.extract_tab_id([1, 2, 3]) is None
        assert session_manager.extract_tab_id(101) == 101
        assert session_manager.extract_tab_id({"tabId": "205"}) == 205
        assert session_manager.extract_tab_id({"tabId": [1, 2]}) is None
        assert session_manager.extract_tab_id({"data": {"tabId": 305}}) == 305
        assert session_manager.extract_tab_id({"payload": {"tabId": "405"}}) == 405
        assert session_manager.extract_tab_id({"result": 505}) == 505
        assert session_manager.extract_tab_id({"data": "corrupted"}) is None
    finally:
        session_manager.clear()
