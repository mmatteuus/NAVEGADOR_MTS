"""Diretório humano de destinos nasce na inicialização real do transporte MCP."""
from __future__ import annotations

import asyncio
import json

from src.mcp.server import MCPServer
from src.mcp.session_manager import session_manager
from src.mcp.ws_bridge import WebSocketBridge


class ExtensionSocket:
    """Socket em memória que observa anúncios sem acessar o navegador pessoal."""
    closed = False

    def __init__(self):
        self.messages = []

    async def send(self, raw):
        self.messages.append(json.loads(raw))


def test_initialize_announces_distinct_named_agents():
    """Dois chats com o mesmo nome permanecem destinos distintos no popup."""
    async def scenario():
        session_manager.clear()
        bridge, extension = WebSocketBridge(), ExtensionSocket()
        bridge.registry.register_extension(extension, {"instanceId": "test-profile"})
        server = MCPServer(ws_bridge=bridge)
        try:
            for sid in ("chat-a", "chat-b"):
                await server.handle_jsonrpc({"id": 1, "method": "initialize",
                    "params": {"clientInfo": {"name": "Chat do navegador"}}}, session_id=sid)
            announced = extension.messages[-1]["payload"]["agents"]
            assert {item["sessionId"] for item in announced} == {"chat-a", "chat-b"}
            assert all(item["agentId"] == "Chat do navegador" for item in announced)
        finally:
            session_manager.clear()
    asyncio.run(scenario())


def test_handshake_contains_directory_before_first_command():
    """O usuário consegue escolher um agente sem executar antes uma ação nele."""
    async def scenario():
        session_manager.clear()
        bridge, extension = WebSocketBridge(), ExtensionSocket()
        server = MCPServer(ws_bridge=bridge)
        try:
            await server.handle_jsonrpc({"id": 1, "method": "initialize",
                "params": {"clientInfo": {"name": "Agente PWA"}}}, session_id="chat-pwa")
            await bridge._process_incoming_message(json.dumps({"type": "client_hello",
                "payload": {"version": server.version, "instanceId": "test-profile"}}), extension)
            agents = extension.messages[-1]["payload"]["agents"]
            assert agents[0]["sessionId"] == "chat-pwa"
            assert agents[0]["agentId"] == "Agente PWA"
        finally:
            session_manager.clear()
    asyncio.run(scenario())
