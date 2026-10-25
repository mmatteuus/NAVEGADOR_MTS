"""Criação via agent_action não concede posse sem popup."""
from __future__ import annotations
import asyncio
import json
from src.mcp.session_manager import session_manager
from src.mcp.ws_action_dispatcher import dispatch_agent_action


def test_ws_new_tab_requires_explicit_assignment() -> None:
    async def run() -> None:
        session_manager.clear()

        class WS:
            def __init__(self): self.sent = []
            async def send(self, payload): self.sent.append(payload)

        async def send_action(*_args, **_kwargs):
            return {"success": True, "data": {"tabId": 909}}

        ws = WS()
        msg = {"id": "new", "action": "browser_manage_tabs", "sessionId": "agent-a",
               "params": {"action": "new", "url": "about:blank"}}
        await dispatch_agent_action(msg, ws, send_action)
        session = session_manager.get_session("agent-a")
        assert session is not None and not session.has_tab(909)
        assert json.loads(ws.sent[0])["success"] is True
        session_manager.clear()

    asyncio.run(run())
