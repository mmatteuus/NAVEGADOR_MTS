"""Suíte Adversarial: Testes de Invasão, Forja e Hijack de Sessão MCP.

Testa empiricamente a proteção anti-forja, rejeição de tentativa de usurpação de sessão
nos argumentos/payloads e isolamento rigoroso de abas entre sessões MCP e WebSocket.
"""
from __future__ import annotations

import asyncio
import json
from src.mcp import MCPToolRouter, WebSocketBridge
from src.mcp.session_manager import session_manager
from src.mcp.ws_action_dispatcher import dispatch_agent_action


def _make_mock_bridge():
    bridge = WebSocketBridge(port=9201)
    bridge._active_socket = object()
    bridge.send_action = lambda a, p, **kw: asyncio.sleep(0, result={"success": True})
    return bridge


def test_adversarial_active_forgery_in_tool_arguments() -> None:
    """Verifica se o Agente B passando sessionId da sess_A nos argumentos é imediatamente bloqueado."""
    async def _run():
        session_manager.clear()
        try:
            session_manager.assign_tab_to_session("sess_A", 101)
            router = MCPToolRouter(ws_bridge=_make_mock_bridge())

            res = await router.dispatch(
                "browser_navigate",
                {"url": "https://attacker.com", "tabId": 101, "sessionId": "sess_A"},
                session_id="sess_B"
            )
            assert res["isError"] is True
            assert "Tentativa de forja de sessão detectada" in res["content"][0]["text"]
        finally:
            session_manager.clear()

    asyncio.run(_run())


def test_adversarial_tab_hijack_between_sessions() -> None:
    """Verifica que o Agente B (sess_B) no transporte não consegue manipular a aba do Agente A (sess_A)."""
    async def _run():
        session_manager.clear()
        try:
            session_manager.assign_tab_to_session("sess_A", 101)
            router = MCPToolRouter(ws_bridge=_make_mock_bridge())

            res = await router.dispatch(
                "browser_navigate",
                {"url": "https://attacker.com", "tabId": 101},
                session_id="sess_B"
            )
            assert res["isError"] is True
            assert "Acesso recusado" in res["content"][0]["text"]
        finally:
            session_manager.clear()

    asyncio.run(_run())


def test_adversarial_tab_hijack_without_session_id_bypass() -> None:
    """Desafio: Agente sem sessão no transporte consegue acessar aba privada da sess_A?"""
    async def _run():
        session_manager.clear()
        try:
            session_manager.assign_tab_to_session("sess_A", 101)
            router = MCPToolRouter(ws_bridge=_make_mock_bridge())
            res = await router.dispatch("browser_navigate", {"url": "https://attacker.com", "tabId": 101})
            assert res.get("isError") is True
            assert "Acesso recusado" in res["content"][0]["text"]
        finally:
            session_manager.clear()

    asyncio.run(_run())


def test_adversarial_tab_assignment_on_browser_manage_tabs_new() -> None:
    """Desafio: Verifica se a aba criada por browser_manage_tabs(new) é vinculada à sessão do transporte."""
    async def _run():
        session_manager.clear()
        try:
            bridge = WebSocketBridge(port=9203)
            bridge._active_socket = object()
            bridge.send_action = lambda a, p, **kw: asyncio.sleep(0, result={"success": True, "tabId": 202, "url": "about:blank"})
            router = MCPToolRouter(ws_bridge=bridge)

            await router.dispatch("browser_manage_tabs", {"action": "new", "url": "https://app.com"}, session_id="sess_A")
            sess = session_manager.get_session("sess_A")
            assert sess is not None and sess.has_tab(202) is True
        finally:
            session_manager.clear()

    asyncio.run(_run())


def test_adversarial_ws_agent_action_forgery_and_tab_validation() -> None:
    """Desafio: Verifica se dispatch_agent_action via WebSocket bloqueia forja e valida posse da aba."""
    class MockWS:
        def __init__(self):
            self.sent = []
        async def send(self, msg: str):
            self.sent.append(msg)

    async def _run():
        session_manager.clear()
        try:
            session_manager.assign_tab_to_session("sess_A", 101)
            mock_ws = MockWS()
            calls = []
            async def mock_send(act, params, session_id=None):
                calls.append({"act": act, "params": params, "session_id": session_id})
                return {"success": True}

            # 1. Tentativa de forja via params
            forgery_msg = {
                "type": "agent_action", "id": "atk_forge", "action": "browser_navigate",
                "sessionId": "sess_B", "params": {"url": "https://evil.com", "sessionId": "sess_A"}
            }
            await dispatch_agent_action(forgery_msg, mock_ws, mock_send)
            assert len(calls) == 0
            assert "FORGERY_DENIED" in json.loads(mock_ws.sent[-1]).get("error", "")

            # 2. Tentativa de acesso a aba alheia
            tab_msg = {
                "type": "agent_action", "id": "atk_tab", "action": "browser_navigate",
                "sessionId": "sess_B", "params": {"url": "https://evil.com", "tabId": 101}
            }
            await dispatch_agent_action(tab_msg, mock_ws, mock_send)
            assert len(calls) == 0
            assert "TAB_ACCESS_DENIED" in json.loads(mock_ws.sent[-1]).get("error", "")
        finally:
            session_manager.clear()

    asyncio.run(_run())
