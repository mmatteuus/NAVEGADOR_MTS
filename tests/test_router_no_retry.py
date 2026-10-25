"""Falhas internas não repetem ações mutáveis nem removem a sessão."""
from __future__ import annotations

import asyncio
from src.mcp.router import MCPToolRouter


def test_internal_type_error_never_replays_without_session():
    """Um erro após enviar clique não provoca segundo envio anônimo."""
    class Bridge:
        is_connected = True
        calls = []

        async def send_action(self, name, args, session_id=None):
            self.calls.append(session_id)
            raise TypeError("Erro depois do envio")

    async def scenario():
        bridge = Bridge()
        result = await MCPToolRouter(ws_bridge=bridge).dispatch("browser_click", {}, session_id="chat-a")
        assert result["isError"]
        assert bridge.calls == ["chat-a"]
    asyncio.run(scenario())
