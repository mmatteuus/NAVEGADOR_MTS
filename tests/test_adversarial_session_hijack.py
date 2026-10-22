"""Suíte Adversarial: Testes de Invasão, Impersonation e Hijack de Sessão MCP.

Testa empiricamente se um agente consegue acessar abas de outro agente,
se chamadas sem sessionId violam abas atribuídas e se o router vincula
corretamente abas novas criadas com sessionId.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from src.mcp import MCPToolRouter, WebSocketBridge
from src.mcp.session_manager import session_manager
from src.mcp.ws_action_dispatcher import dispatch_agent_action


def test_adversarial_tab_hijack_between_sessions() -> None:
    """Verifica que o Agente B (sess_B) não consegue manipular a aba do Agente A (sess_A)."""
    async def _run():
        session_manager.clear()
        try:
            session_manager.assign_tab_to_session("sess_A", 101)
            bridge = WebSocketBridge(port=9201)
            bridge._active_socket = object()
            bridge.send_action = lambda a, p, **kw: asyncio.sleep(0, result={"success": True})
            router = MCPToolRouter(ws_bridge=bridge)

            res = await router.dispatch(
                "browser_navigate",
                {"url": "https://attacker.com", "tabId": 101, "sessionId": "sess_B"}
            )
            assert res["isError"] is True
            assert "Acesso recusado" in res["content"][0]["text"]
        finally:
            session_manager.clear()

    asyncio.run(_run())


def test_adversarial_tab_hijack_without_session_id_bypass() -> None:
    """Desafio: Agente sem sessionId consegue acessar aba privada da sess_A?"""
    async def _run():
        session_manager.clear()
        try:
            session_manager.assign_tab_to_session("sess_A", 101)
            bridge = WebSocketBridge(port=9202)
            bridge._active_socket = object()
            bridge.send_action = lambda a, p, **kw: asyncio.sleep(0, result={"success": True})
            router = MCPToolRouter(ws_bridge=bridge)

            return await router.dispatch(
                "browser_navigate",
                {"url": "https://attacker.com", "tabId": 101}
            )
        finally:
            session_manager.clear()

    res = asyncio.run(_run())
    assert res.get("isError") is True, "Chamada anônima a aba privada de outra sessão deve ser bloqueada"
    assert "Acesso recusado" in res["content"][0]["text"]


def test_adversarial_tab_assignment_on_browser_manage_tabs_new() -> None:
    """Desafio: Verifica se a aba criada por browser_manage_tabs(new) é vinculada à sessão."""
    async def _run():
        session_manager.clear()
        try:
            bridge = WebSocketBridge(port=9203)
            bridge._active_socket = object()
            bridge.send_action = lambda a, p, **kw: asyncio.sleep(0, result={"success": True, "tabId": 202, "url": "about:blank"})
            router = MCPToolRouter(ws_bridge=bridge)

            await router.dispatch(
                "browser_manage_tabs",
                {"action": "new", "url": "https://app.com", "sessionId": "sess_A"},
                session_id="sess_A"
            )

            sess = session_manager.get_session("sess_A")
            return sess.has_tab(202) if sess else False
        finally:
            session_manager.clear()

    assigned = asyncio.run(_run())
    assert assigned is True, "Aba criada via new deve ser vinculada à sessão solicitante"


def test_adversarial_ws_agent_action_bypasses_tab_validation() -> None:
    """Desafio: Verifica se dispatch_agent_action via WebSocket valida posse da aba."""
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
            executed_calls = []

            async def mock_send_action(act, params, session_id=None):
                executed_calls.append({"act": act, "params": params, "session_id": session_id})
                return {"success": True}

            data = {
                "type": "agent_action",
                "id": "attack_1",
                "action": "browser_navigate",
                "params": {"url": "https://evil.com", "tabId": 101},
                "sessionId": "sess_B"
            }

            await dispatch_agent_action(data, mock_ws, mock_send_action)
            return executed_calls, mock_ws.sent
        finally:
            session_manager.clear()

    executed_calls, sent = asyncio.run(_run())
    assert len(executed_calls) == 0, "Ação em aba alheia não deve ser despachada para a extensão"
    assert len(sent) == 1
    resp = json.loads(sent[0])
    assert resp.get("success") is False
    assert "TAB_ACCESS_DENIED" in resp.get("error", "")
