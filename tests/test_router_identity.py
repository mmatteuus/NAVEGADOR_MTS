"""Regressões para identidade confiável no MCPToolRouter."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.mcp.router import MCPToolRouter
from src.mcp.session_context import reset_current_session_id, set_current_session_id


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["sessionId", "session_id"])
async def test_alias_sem_transporte_rejeitado_sem_chamar_bridge(key: str) -> None:
    bridge = AsyncMock()
    bridge.is_connected = True
    router = MCPToolRouter(ws_bridge=bridge)
    result = await router.dispatch("browser_navigate", {"url": "https://x", key: "agent-a"})
    assert result["isError"] is True
    bridge.send_action.assert_not_awaited()


@pytest.mark.asyncio
async def test_aliases_divergentes_rejeitados_antes_do_bridge() -> None:
    bridge = AsyncMock()
    bridge.is_connected = True
    router = MCPToolRouter(ws_bridge=bridge)
    result = await router.dispatch(
        "browser_navigate", {"url": "https://x", "sessionId": "a", "session_id": "b"}, session_id="a"
    )
    assert result["isError"] is True
    bridge.send_action.assert_not_awaited()


@pytest.mark.asyncio
async def test_parametro_e_contexto_confiaveis_sao_aceitos() -> None:
    bridge = AsyncMock()
    bridge.is_connected = True
    bridge.send_action.return_value = {"success": True, "data": {"ok": True}}
    router = MCPToolRouter(ws_bridge=bridge)
    result = await router.dispatch("browser_navigate", {"url": "https://x", "sessionId": "agent-a"}, session_id="agent-a")
    assert result["isError"] is False
    assert '"ok": true' in result["content"][0]["text"]
    bridge.send_action.assert_awaited_once()
    token = set_current_session_id("agent-b")
    try:
        result = await router.dispatch("browser_navigate", {"url": "https://x", "session_id": "agent-b"})
        assert result["isError"] is False
        assert '"ok": true' in result["content"][0]["text"]
    finally:
        reset_current_session_id(token)


@pytest.mark.asyncio
async def test_chamada_anonima_sem_alias_preserva_compatibilidade() -> None:
    bridge = AsyncMock()
    bridge.is_connected = True
    bridge.send_action.return_value = {"success": True, "data": {"ok": True}}
    router = MCPToolRouter(ws_bridge=bridge)
    result = await router.dispatch("browser_navigate", {"url": "https://x"})
    assert result["isError"] is False
    assert '"ok": true' in result["content"][0]["text"]
    bridge.send_action.assert_awaited_once_with("browser_navigate", {"url": "https://x"}, session_id=None)
