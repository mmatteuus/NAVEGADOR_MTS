"""Suíte de Teste de Estresse: 20 Ciclos de Start/Stop.

Executa 20 ciclos repetidos e ininterruptos de inicialização e encerramento,
garantindo que 0 processos órfãos permaneçam no SO e 0 portas fiquem presas.
"""

from __future__ import annotations

import asyncio
import socket
import psutil
from src.core.resilience import configure_socket_reuse
from src.mcp.ws_bridge import WebSocketBridge
from tests.test_harness import create_dummy_supervisor, is_port_in_use


def test_twenty_start_stop_supervisor_cycles() -> None:
    """Executa 20 ciclos de start/stop de processos verificando 0 órfãos."""
    supervisor = create_dummy_supervisor("stress_worker")
    spawned_pids: list[int] = []

    for cycle in range(1, 21):
        assert supervisor.start(), f"Falha ao iniciar processo no ciclo {cycle}."
        pid = supervisor._popen.pid if supervisor._popen else 0
        assert pid > 0 and supervisor.is_alive(), f"Processo deve estar vivo no ciclo {cycle}."
        spawned_pids.append(pid)

        # Encerramento gracioso em árvore
        supervisor.terminate_tree(timeout=1.0)
        assert not supervisor.is_alive(), f"Processo ainda vivo após parada no ciclo {cycle}."

    # Validação final: nenhum dos 20 processos gerados pode continuar ativo no Windows
    for pid in spawned_pids:
        assert not psutil.pid_exists(pid) or not psutil.Process(pid).is_running(), (
            f"PROCESSO ÓRFÃO DETECTADO: PID {pid} continua ativo após o teste de estresse!"
        )


def test_twenty_start_stop_socket_port_cycles(dynamic_port: int) -> None:
    """Valida 20 ciclos consecutivos de bind/close sem erro de porta presa (SO_REUSEADDR)."""
    for cycle in range(1, 21):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        configure_socket_reuse(sock)

        # Deve conseguir fazer bind imediatamente sem EADDRINUSE
        try:
            sock.bind(("127.0.0.1", dynamic_port))
            sock.listen(5)
        except OSError as exc:
            raise AssertionError(f"Porta {dynamic_port} presa no ciclo {cycle}: {exc}") from exc
        finally:
            sock.close()


def test_twenty_start_stop_ws_bridge_cycles(dynamic_port: int) -> None:
    """Testa 20 ciclos de inicialização e desligamento assíncrono do WebSocketBridge."""
    bridge = WebSocketBridge(host="127.0.0.1", port=dynamic_port)

    async def _run() -> None:
        for cycle in range(1, 21):
            await bridge.start()
            assert bridge.server is not None, f"Servidor não inicializou no ciclo {cycle}."

            await bridge.stop()
            assert bridge.server is None, f"Servidor não finalizou no ciclo {cycle}."
            assert not is_port_in_use(dynamic_port), (
                f"Porta {dynamic_port} permaneceu ocupada após parada no ciclo {cycle}."
            )

    asyncio.run(_run())
