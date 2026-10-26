"""Suíte de Testes para a verificação de atividade do Hub MCP (hub_client.py).

Valida a função is_hub_running em cenários de sucesso (pong recebido),
porta fechada, resposta inválida, timeout e erro de conexão.
"""

from __future__ import annotations

import asyncio
import json
import pytest
from websockets.asyncio.server import serve
from src.mcp.hub_client import is_hub_running
from src.mcp.ws_bridge import WebSocketBridge


def test_is_hub_running_active_bridge(dynamic_port: int) -> None:
    """Valida retorno True quando o WebSocketBridge ativo responde ping com pong."""
    async def _run():
        bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)
        await bridge.start()
        try:
            running = await is_hub_running("127.0.0.1", dynamic_port, timeout=1.0)
            assert running is True
        finally:
            await bridge.stop()

    asyncio.run(_run())


def test_is_hub_running_connection_refused(dynamic_port: int) -> None:
    """Valida retorno False quando não há servidor escutando na porta especificada."""
    async def _run():
        running = await is_hub_running("127.0.0.1", dynamic_port, timeout=0.2)
        assert running is False

    asyncio.run(_run())


def test_is_hub_running_non_pong_response(dynamic_port: int) -> None:
    """Valida retorno False quando a resposta do servidor WebSocket não contém 'pong'."""
    async def _handler(websocket):
        await websocket.recv()
        await websocket.send(json.dumps({"type": "welcome", "msg": "hello"}))

    async def _run():
        async with serve(_handler, "127.0.0.1", dynamic_port):
            running = await is_hub_running("127.0.0.1", dynamic_port, timeout=1.0)
            assert running is False

    asyncio.run(_run())


def test_is_hub_running_timeout(dynamic_port: int) -> None:
    """Valida retorno False quando o servidor demora mais do que o timeout especificado."""
    async def _handler(websocket):
        await websocket.recv()
        await asyncio.sleep(2.0)

    async def _run():
        async with serve(_handler, "127.0.0.1", dynamic_port):
            running = await is_hub_running("127.0.0.1", dynamic_port, timeout=0.1)
            assert running is False

    asyncio.run(_run())


def test_is_hub_running_invalid_host() -> None:
    """Valida retorno False quando um endereço de host inválido/inexistente é fornecido."""
    async def _run():
        running = await is_hub_running("invalid_host_123456789.local", 3456, timeout=0.1)
        assert running is False

    asyncio.run(_run())
