"""Suíte de Testes para Despacho de Comandos de Agentes via WebSocket Bridge.

Valida que comandos com type: agent_action enviados por agentes de IA são roteados
para a extensão (browser_*) ou para o módulo de computador (computer_*).
"""

from __future__ import annotations

import asyncio
import json
import pytest
from websockets.asyncio.client import connect
from src.mcp.ws_bridge import WebSocketBridge
from src.computer.safety_gate import safety_gate


def test_agent_action_browser_routing(dynamic_port: int) -> None:
    """Valida o encaminhamento de uma ação browser_* para a extensão do navegador."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"

        # 1. Extensão conecta e faz handshake
        async with connect(uri) as ext_ws:
            await ext_ws.send(json.dumps({"type": "client_hello", "payload": {"version": "2.0.0"}}))
            raw_srv = await ext_ws.recv()
            assert json.loads(raw_srv)["type"] == "server_hello"
            assert bridge.is_connected

            # 2. Agente de IA conecta em socket separado
            async with connect(uri) as agent_ws:
                # Agente envia comando browser_navigate
                agent_msg = {
                    "type": "agent_action",
                    "id": "agent_req_1",
                    "action": "browser_navigate",
                    "params": {"url": "https://example.com"}
                }
                await agent_ws.send(json.dumps(agent_msg))

                # Extensão recebe o comando despachado pelo bridge
                ext_cmd_raw = await ext_ws.recv()
                ext_cmd = json.loads(ext_cmd_raw)
                assert ext_cmd["action"] == "browser_navigate"
                assert ext_cmd["payload"]["url"] == "https://example.com"

                # Extensão responde
                reply = {
                    "type": "browser_response",
                    "id": ext_cmd["id"],
                    "payload": {"requestId": ext_cmd["id"], "result": {"navigated": True}}
                }
                await ext_ws.send(json.dumps(reply))

                # Agente recebe a resposta com sucesso
                agent_res_raw = await agent_ws.recv()
                agent_res = json.loads(agent_res_raw)
                assert agent_res["success"] is True
                assert agent_res["result"] == {"navigated": True}

        await bridge.stop()

    asyncio.run(_run())


def test_agent_action_computer_routing(dynamic_port: int) -> None:
    """Valida o despacho de ações computer_* respeitando a trava Fail-Closed."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"

        async with connect(uri) as agent_ws:
            # Trava desativada: deve retornar erro de segurança amigável
            safety_gate.revoke("Teste")
            agent_msg = {
                "type": "agent_action",
                "id": "agent_comp_1",
                "action": "computer_mouse_move",
                "params": {"x": 100, "y": 100}
            }
            await agent_ws.send(json.dumps(agent_msg))

            res_raw = await agent_ws.recv()
            res = json.loads(res_raw)
            assert res["success"] is False
            assert "ERRO_SEGURANCA" in res["result"]["error"]

            # Trava ativada: deve executar com sucesso
            safety_gate.authorize()
            await agent_ws.send(json.dumps(agent_msg))
            res_raw2 = await agent_ws.recv()
            res2 = json.loads(res_raw2)
            assert res2["success"] is True

        await bridge.stop()

    asyncio.run(_run())

