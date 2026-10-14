"""Suíte Adversarial de Caos em WebSocket e Detecção de Queda de Pulso.

Desafia a resiliência a desconexão abrupta com ação em voo (in-flight),
comprova reconexão em <= 5s e detecção matemática de perda de pulso em <= 10s.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import List
import pytest
from websockets.asyncio.client import connect

from src.core.heartbeat import HeartbeatConfig, HeartbeatManager
from src.mcp.ws_bridge import WebSocketBridge


def test_adversarial_ws_abrupt_disconnect_and_reconnection(dynamic_port: int) -> None:
    """Simula corte abrupto de conexão durante ação pendente e valida auto-cura em <= 5s."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _scenario() -> None:
        await bridge.start()
        uri = f"ws://127.0.0.1:{dynamic_port}"

        # 1. Conecta o cliente simulado
        client1 = await connect(uri)
        await client1.send(json.dumps({"type": "client_hello", "payload": {}}))
        await client1.recv()  # server_hello
        assert bridge.is_connected

        # 2. Inicia uma ação pendente e desconecta abruptamente o cliente
        action_task = asyncio.create_task(bridge.send_action("teste_corte", {}, timeout=0.8))
        await client1.close()  # Queda abrupta da conexão

        # A ação pendente deve falhar de forma limpa sem corromper a ponte
        with pytest.raises((asyncio.TimeoutError, ConnectionError, RuntimeError)):
            await action_task

        assert not bridge.is_connected

        # 3. Auto-recuperação: reconexão de novo cliente em tempo <= 5.0s
        t_reconnect_start = time.time()
        client2 = await connect(uri)
        await client2.send(json.dumps({"type": "client_hello", "payload": {}}))
        hello_resp = json.loads(await client2.recv())
        reconnect_elapsed = time.time() - t_reconnect_start

        assert hello_resp.get("type") == "server_hello"
        assert bridge.is_connected
        assert reconnect_elapsed <= 5.0, f"Reconexão demorou {reconnect_elapsed:.2f}s (> 5s)!"

        await client2.close()
        await bridge.stop()

    asyncio.run(_scenario())


def test_adversarial_heartbeat_drop_detection_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Comprova que a queda é detectada em <= 10s e recuperada em <= 5s."""
    falhas: List[str] = []
    # Intervalo de 3s e timeout de 2s (configuração padrão oficial de produção)
    cfg = HeartbeatConfig(interval_seconds=3.0, timeout_seconds=2.0, max_missed_pings=2)
    hb = HeartbeatManager(config=cfg, on_failure_callback=falhas.append)

    simulated_time = 1000.0
    monkeypatch.setattr(time, "time", lambda: simulated_time)

    # t = 0s: 1º ping emitido
    hb.create_ping_payload()

    # t = 2.1s: timeout do 1º ping estourado (missed = 1)
    simulated_time = 1002.1
    saudavel_t2 = hb.check_health()
    assert saudavel_t2 is True
    assert hb.missed_count == 1

    # t = 3.0s: 2º ping emitido
    simulated_time = 1003.0
    hb.create_ping_payload()

    # t = 5.1s: timeout do 2º ping estourado (missed = 2 -> falha detectada!)
    simulated_time = 1005.1
    saudavel_t5 = hb.check_health()
    detection_time = simulated_time - 1000.0

    assert saudavel_t5 is False
    assert not hb.is_healthy
    assert len(falhas) == 1
    assert detection_time <= 10.0, f"Tempo de detecção de {detection_time}s excedeu o limite de 10s."

    # Auto-cura imediata ao receber pong
    latency = hb.record_pong()
    assert hb.is_healthy
    assert hb.missed_count == 0
