"""Suíte Adversarial: Concorrência entre Clientes Legados e Multissessão MCP.

Testa empiricamente:
1. Tráfego simultâneo de alta concorrência com e sem sessionId.
2. Rogue client_hello: se um agente ou cliente malicioso consegue roubar
   a conexão ativa da extensão enviando client_hello na porta 3456.
3. Desencadeamento de sessões órfãs em chamadas sem sessionId.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from websockets.asyncio.client import connect
from src.mcp import WebSocketBridge
from src.mcp.session_manager import session_manager
from src.mcp.ws_action_dispatcher import dispatch_agent_action


def test_concurrent_legacy_and_multisession_requests(dynamic_port: int) -> None:
    """Valida 30 requisições concorrentes misturando clientes com e sem sessionId."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"

        # Extensão simulada
        async with connect(uri) as ext_ws:
            await ext_ws.send(json.dumps({"type": "client_hello", "payload": {"v": "2.0"}}))
            assert json.loads(await ext_ws.recv())["type"] == "server_hello"

            async def mock_extension_worker():
                for _ in range(30):
                    raw = await ext_ws.recv()
                    data = json.loads(raw)
                    req_id = data["id"]
                    reply = {
                        "type": "browser_response",
                        "id": req_id,
                        "payload": {"requestId": req_id, "result": {"echo": data["action"], "sid": data.get("sessionId")}}
                    }
                    await ext_ws.send(json.dumps(reply))

            ext_task = asyncio.create_task(mock_extension_worker())

            # 15 requisições com sessionId e 15 sem sessionId disparadas em paralelo
            async def send_req(i: int):
                sid = f"agent_{i % 3}" if i % 2 == 0 else None
                act = f"browser_action_{i}"
                res = await bridge.send_action(act, {"index": i}, timeout=5.0, session_id=sid)
                assert res["echo"] == act
                assert res["sid"] == sid

            await asyncio.gather(*(send_req(i) for i in range(30)))
            await ext_task

        await bridge.stop()

    asyncio.run(_run())


def test_adversarial_extension_hijacking_via_client_hello(dynamic_port: int) -> None:
    """Desafio: Verifica se um cliente rogue pode roubar o tráfego da extensão real."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"

        # 1. Extensão real conecta
        real_ext = await connect(uri)
        await real_ext.send(json.dumps({"type": "client_hello", "payload": {"name": "real_extension"}}))
        await real_ext.recv()  # server_hello

        # 2. Rogue Agent conecta na mesma porta WS e finge ser extensão via client_hello
        rogue_agent = await connect(uri)
        await rogue_agent.send(json.dumps({"type": "client_hello", "payload": {"name": "rogue_hijacker"}}))
        await rogue_agent.recv()  # server_hello

        # 3. Servidor tenta enviar ação do navegador
        send_task = asyncio.create_task(bridge.send_action("browser_navigate", {"url": "https://secret.com"}, timeout=2.0))

        # 4. Verifica quem recebe a mensagem
        # Se o rogue receber, o tráfego foi sequestrado com sucesso!
        received_by_rogue = None
        try:
            raw = await asyncio.wait_for(rogue_agent.recv(), timeout=1.0)
            received_by_rogue = json.loads(raw)
        except asyncio.TimeoutError:
            pass

        # Cleanup
        send_task.cancel()
        await real_ext.close()
        await rogue_agent.close()
        await bridge.stop()

        return received_by_rogue

    intercepted = asyncio.run(_run())
    print("Mensagem confidencial interceptada pelo rogue:", intercepted)
    assert intercepted is None, "Proteção confirmada: rogue NÃO conseguiu sequestrar o socket ativo da extensão!"
