"""Uma extensão nunca conclui o comando enviado a outro navegador."""
from __future__ import annotations

import asyncio
import json

from src.mcp.ws_bridge import WebSocketBridge


class Socket:
    """Registra a conexão escolhida sem tocar em perfis do usuário."""
    closed = False

    def __init__(self):
        self.sent = []

    async def send(self, raw):
        self.sent.append(json.loads(raw))


def test_response_from_other_extension_cannot_finish_command():
    """O ID da requisição sozinho não autoriza um socket a fornecer seu resultado."""
    async def scenario():
        bridge = WebSocketBridge()
        first, second = Socket(), Socket()
        bridge.registry.register_extension(first, {"instanceId": "first", "grantedTabIds": [11]})
        bridge.registry.register_extension(second, {"instanceId": "second", "grantedTabIds": [22]})
        command = asyncio.create_task(bridge.send_action("browser_get_text", {"tabId": 11}, session_id="agent-a"))
        try:
            await asyncio.sleep(0)
            request = first.sent[0]["id"]
            forged = json.dumps({"type": "browser_response", "id": request,
                                 "payload": {"result": {"text": "wrong browser"}}})
            await bridge._process_incoming_message(forged, second)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not command.done(), "Resposta de outro navegador concluiu uma ação alheia"
            correct = json.dumps({"type": "browser_response", "id": request,
                                  "payload": {"result": {"text": "assigned browser"}}})
            await bridge._process_incoming_message(correct, first)
            assert (await command)["text"] == "assigned browser"
        finally:
            command.cancel()
            await asyncio.gather(command, return_exceptions=True)
    asyncio.run(scenario())
