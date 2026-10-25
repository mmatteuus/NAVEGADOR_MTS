"""Conexões de agentes sem cabeçalho não compartilham entrada virtual."""
from __future__ import annotations

import asyncio
import json
from src.mcp.ws_bridge import WebSocketBridge
from src.mcp.session_manager import session_manager


class Socket:
    """Captura apenas respostas públicas, sem controlar o Windows."""
    def __init__(self):
        self.responses = []

    async def send(self, data):
        self.responses.append(json.loads(data))


def test_websocket_session_is_stable_distinct_and_cannot_be_swapped():
    """Cada conexão recebe identidade própria; trocar o ID no meio é recusado."""
    async def scenario():
        bridge = WebSocketBridge()
        first, second = Socket(), Socket()
        request = {"type": "agent_action", "id": "status", "action": "computer_get_status", "params": {}}
        try:
            for socket in (first, second, first):
                await bridge._process_incoming_message(json.dumps(request), socket)
            sid1, sid2 = bridge._agent_sessions[first], bridge._agent_sessions[second]
            assert sid1 != sid2
            assert first.responses[-1]["success"]
            await bridge._process_incoming_message(json.dumps({**request, "sessionId": sid2}), first)
            assert not first.responses[-1]["success"]
            assert "FORGERY_DENIED" in first.responses[-1]["error"]
            assert bridge._agent_sessions[first] == sid1
        finally:
            session_manager.clear()
    asyncio.run(scenario())
