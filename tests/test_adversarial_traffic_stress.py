"""Suíte de Teste de Estresse Adversarial com Tráfego Real em 20 Ciclos.

Desafia o ciclo de vida do WebSocketBridge e do ProcessSupervisor submetendo-os
a tráfego ativo de mensagens JSON durante 20 reinicializações consecutivas.
Garante 0 processos órfãos, 0 sockets presos e tempo de auto-cura <= 5s.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import List
import psutil
import pytest
from websockets.asyncio.client import connect

from src.mcp.ws_bridge import WebSocketBridge
from tests.test_harness import create_dummy_supervisor, is_port_in_use


def test_twenty_cycles_with_active_websocket_traffic(dynamic_port: int) -> None:
    """Executa 20 ciclos consecutivos de start/traffic/stop no WebSocketBridge."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)
    uri = f"ws://127.0.0.1:{dynamic_port}"

    async def _cycle(cycle_num: int) -> None:
        # 1. Inicia o servidor
        await bridge.start()
        assert bridge.server is not None, f"Servidor não inicializou no ciclo {cycle_num}."

        # 2. Conecta o cliente e transmite tráfego ativo
        async with connect(uri) as ws:
            # Envia hello
            await ws.send(json.dumps({"type": "client_hello", "payload": {"cycle": cycle_num}}))
            raw_hello = await ws.recv()
            hello_data = json.loads(raw_hello)
            assert hello_data["type"] == "server_hello"

            # Envia ping
            await ws.send(json.dumps({"type": "ping", "ts": cycle_num * 1000}))
            raw_pong = await ws.recv()
            pong_data = json.loads(raw_pong)
            assert pong_data["type"] == "pong"
            assert pong_data["ts"] == cycle_num * 1000

        # 3. Encerra o servidor
        await bridge.stop()
        assert bridge.server is None, f"Servidor não finalizou no ciclo {cycle_num}."
        assert not is_port_in_use(dynamic_port), (
            f"Porta {dynamic_port} permaneceu presa após ciclo {cycle_num}!"
        )

    async def _run_all() -> None:
        for c in range(1, 21):
            await _cycle(c)

    t0 = time.time()
    asyncio.run(_run_all())
    total_elapsed = time.time() - t0

    # 20 ciclos de conexão, envio, recepção e encerramento devem ser rápidos e eficientes
    assert total_elapsed < 15.0, f"Tempo total excessivo ({total_elapsed:.2f}s para 20 ciclos)."


def test_twenty_cycles_supervisor_with_abrupt_kill_and_recovery(
    process_cleanup_tracker: List[psutil.Process],
) -> None:
    """Executa 20 ciclos de morte abrupta (kill -9) com auto-cura e 0 órfãos."""
    supervisor = create_dummy_supervisor("adversarial_stress_worker")
    assert supervisor.start()

    created_pids: List[int] = []

    for cycle in range(1, 21):
        assert supervisor.is_alive()
        pid = supervisor._popen.pid if supervisor._popen else 0
        assert pid > 0
        created_pids.append(pid)

        # Injeta falha fatal: mata abruptamente via kernel
        proc = psutil.Process(pid)
        process_cleanup_tracker.append(proc)
        proc.kill()
        try:
            proc.wait(timeout=1.0)
        except (psutil.TimeoutExpired, psutil.NoSuchProcess):
            pass
        assert not supervisor.is_alive(), f"Processo ainda vivo após kill no ciclo {cycle}."

        # Auto-cura imediata em tempo <= 5.0s
        t_start = time.time()
        restarted = supervisor.restart(reason=f"Recuperação ciclo {cycle}")
        t_recovery = time.time() - t_start

        assert restarted, f"Falha na auto-cura no ciclo {cycle}."
        assert supervisor.is_alive(), f"Supervisor não ativo após restart no ciclo {cycle}."
        assert t_recovery <= 5.0, (
            f"Tempo de auto-cura ({t_recovery:.2f}s) excedeu 5s no ciclo {cycle}."
        )

    # Limpeza final
    supervisor.terminate_tree()
    assert not supervisor.is_alive()

    # Comprova que NENHUM dos 20 PIDs sobreviveu como processo órfão
    for pid in created_pids:
        assert not psutil.pid_exists(pid), (
            f"PROCESSO ÓRFÃO ENCONTRADO: PID {pid} sobreviveu ao teste de estresse!"
        )
