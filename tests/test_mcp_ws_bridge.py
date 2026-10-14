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
