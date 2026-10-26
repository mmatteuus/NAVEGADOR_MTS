"""Suíte de Testes da Ponte WebSocket do Servidor MCP (WebSocket Bridge).

Valida conexão bidirecional com a extensão, handshakes, ping/pong,
despacho assíncrono de comandos e tratamento de erros e timeouts.
"""

from __future__ import annotations

import asyncio
import json
import pytest
from websockets.asyncio.client import connect
from src.mcp.ws_bridge import WebSocketBridge


def test_websocket_bridge_end_to_end(dynamic_port: int) -> None:
    """Valida conexão bidirecional, handshake client_hello e envio de ação."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        assert not bridge.is_connected

        uri = f"ws://127.0.0.1:{dynamic_port}"
        async with connect(uri) as ws:
            # 1. Envia client_hello
            hello = {"type": "client_hello", "payload": {"extensionVersion": "2.0.0"}}
            await ws.send(json.dumps(hello))

            # 2. Recebe server_hello
            raw_srv = await ws.recv()
            srv_data = json.loads(raw_srv)
            assert srv_data["type"] == "server_hello"
            assert bridge.is_connected

            # 3. Testa Ping do cliente
            await ws.send(json.dumps({"type": "ping", "ts": 12345}))
            pong_raw = await ws.recv()
            pong_data = json.loads(pong_raw)
            assert pong_data["type"] == "pong" and pong_data["ts"] == 12345

            # 4. Envia ação do servidor para a extensão
            async def mock_extension_worker():
                cmd_raw = await ws.recv()
                cmd = json.loads(cmd_raw)
                assert cmd["action"] == "click"
                resp = {
                    "type": "browser_response",
                    "id": cmd["id"],
                    "payload": {"requestId": cmd["id"], "result": {"clicked": True}}
                }
                await ws.send(json.dumps(resp))

            worker_task = asyncio.create_task(mock_extension_worker())
            action_res = await bridge.send_action("click", {"selector": "#btn-test"})
            assert action_res == {"clicked": True}
            await worker_task

        await bridge.stop()

    asyncio.run(_run())


def test_websocket_bridge_timeout_and_error(dynamic_port: int) -> None:
    """Valida detecção de timeout de ação e tratamento de erro emitido pela extensão."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"
        async with connect(uri) as ws:
            await ws.send(json.dumps({"type": "client_hello"}))
            await ws.recv()  # server_hello

            # 1. Timeout de ação quando o cliente não responde
            with pytest.raises(asyncio.TimeoutError):
                await bridge.send_action("hang_action", {}, timeout=0.1)

            # Consome o comando pendente
            await ws.recv()

            # 2. Resposta de erro pela extensão
            async def error_responder():
                cmd = json.loads(await ws.recv())
                err_resp = {
                    "type": "browser_response",
                    "id": cmd["id"],
                    "payload": {"requestId": cmd["id"], "error": "Elemento não encontrado no DOM"}
                }
                await ws.send(json.dumps(err_resp))

            err_task = asyncio.create_task(error_responder())
            with pytest.raises(RuntimeError) as exc_info:
                await bridge.send_action("failing_action", {})
            assert "Elemento não encontrado" in str(exc_info.value)
            await err_task

        await bridge.stop()

    asyncio.run(_run())


def test_websocket_bridge_init() -> None:
    """Valida a inicialização padrão e customizada da classe WebSocketBridge."""
    bridge = WebSocketBridge()
    assert bridge.host == "127.0.0.1" and bridge.port == 3456
    assert bridge.server is None and bridge.registry is not None
    assert bridge._pending_requests == {} and bridge.last_latency_ms == 0.0
    assert bridge._reload_policy is not None and not bridge.is_connected

    custom_bridge = WebSocketBridge(host="192.168.1.1", port=8080)
    assert custom_bridge.host == "192.168.1.1" and custom_bridge.port == 8080


def test_websocket_bridge_port_hopping(dynamic_port: int) -> None:
    """Valida que o WebSocketBridge pula automaticamente para a próxima porta se a inicial estiver ocupada."""
    import socket

    # Ocupa propositalmente a porta dynamic_port
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", dynamic_port))
    blocker.listen(1)

    try:
        bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

        async def _run():
            bound_port = await bridge.start(max_ports=5)
            assert bound_port > dynamic_port
            assert bridge.port == bound_port
            await bridge.stop()

        asyncio.run(_run())
    finally:
        blocker.close()
