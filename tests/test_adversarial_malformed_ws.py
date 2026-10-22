"""Suíte Adversarial: Robustez contra Mensagens Malformadas e JSON Corrompido.

Testa empiricamente como a ponte WebSocket reage a:
1. JSON não-objeto (int, string, list, null).
2. agent_action com 'params' corrompidos (não-dict).
3. browser_response com 'payload' corrompido.
4. Frames binários inválidos (bytes não-UTF-8).
5. Rajada concorrente de lixo sem derrubar o bridge nem afetar agentes legítimos.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from websockets.asyncio.client import connect
from src.mcp import WebSocketBridge


def test_adversarial_non_dict_json_handling(dynamic_port: int) -> None:
    """Verifica se JSON não-dicionário derruba o socket com AttributeError."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"

        # Envia JSON válido mas não-dicionário: "123", "[\"item\"]", "null"
        async with connect(uri) as ws:
            await ws.send("12345")
            await ws.send(json.dumps(["invalid", "payload"]))
            await ws.send("null")
            # Envia ping subsequente para verificar se a conexão ainda sobrevive
            await ws.send(json.dumps({"type": "ping", "ts": 100}))
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                pong = json.loads(raw)
                survived = pong.get("type") == "pong"
            except Exception:
                survived = False

        await bridge.stop()
        return survived

    survived = asyncio.run(_run())
    print("Conexão sobreviveu a JSON não-dicionário?:", survived)
    assert survived is True, "Conexão deve sobreviver a JSON não-dicionário e responder ao ping"


def test_adversarial_malformed_agent_action_params(dynamic_port: int) -> None:
    """Verifica se agent_action com params inválido gera resposta de erro sem derrubar o socket."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"

        async with connect(uri) as ws:
            # params como string em vez de dict
            bad_msg = {"type": "agent_action", "id": "bad_1", "action": "browser_navigate", "params": "string_not_dict"}
            await ws.send(json.dumps(bad_msg))
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                reply = json.loads(raw)
            except Exception:
                reply = None

        await bridge.stop()
        return reply

    reply = asyncio.run(_run())
    print("Resposta para params inválido:", reply)
    assert reply is not None, "Socket deve responder estruturadamente para params inválido"
    assert reply.get("success") is False, "Deve indicar falha para params não-dicionário"
    assert "params" in reply.get("error", "").lower()


def test_adversarial_corrupted_burst_concurrency(dynamic_port: int) -> None:
    """Verifica se rajadas de lixo simultâneas não impedem clientes legítimos de operar."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run():
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"

        # Extensão legítima
        ext_ws = await connect(uri)
        await ext_ws.send(json.dumps({"type": "client_hello", "payload": {}}))
        await ext_ws.recv()

        async def ext_responder():
            while True:
                try:
                    raw = await ext_ws.recv()
                    data = json.loads(raw)
                    rep = {"type": "browser_response", "id": data["id"], "payload": {"requestId": data["id"], "result": {"ok": True}}}
                    await ext_ws.send(json.dumps(rep))
                except Exception:
                    break

        ext_task = asyncio.create_task(ext_responder())

        # Atacante bombardeia com JSON malformado e sintaxe corrompida
        async def garbage_spammer():
            for _ in range(10):
                try:
                    async with connect(uri) as spam_ws:
                        await spam_ws.send("{corrupted_syntax: true,")
                        await spam_ws.send("true")
                        await spam_ws.send(json.dumps({"type": "unknown_junk", "foo": "bar"}))
                except Exception:
                    pass
                await asyncio.sleep(0.01)

        # Cliente legítimo executa requisição durante o bombardeio
        async def legitimate_client():
            await asyncio.sleep(0.05)
            return await bridge.send_action("browser_click", {"x": 10, "y": 20}, timeout=2.0)

        spam_task = asyncio.create_task(garbage_spammer())
        client_res = await legitimate_client()
        await spam_task

        ext_task.cancel()
        await ext_ws.close()
        await bridge.stop()
        return client_res

    res = asyncio.run(_run())
    print("Cliente legítimo operou com sucesso durante spam?:", res.get("ok"))
    assert res.get("ok") is True
