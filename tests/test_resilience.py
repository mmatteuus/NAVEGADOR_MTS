"""Suíte de Testes de Resiliência e Auto-Cura (Self-Healing).

Testa injeção de falhas (derrubada de WebSocket, morte de processo filho)
e valida que o sistema detecta e recupera o serviço em tempo <= 5 segundos.
"""

from __future__ import annotations

import time
from typing import Any, List
import psutil
from src.core.heartbeat import HeartbeatConfig, HeartbeatManager
from src.core.message_buffer import MessageBuffer
from src.core.resilience import ConnectionState, ResilienceManager
from tests.test_harness import create_dummy_supervisor


def test_process_death_and_auto_restart(process_cleanup_tracker: List[psutil.Process]) -> None:
    """Verifica que a morte abrupta de um processo filho é recuperada em <= 2s."""
    supervisor = create_dummy_supervisor("test_worker")
    assert supervisor.start(), "Falha ao iniciar o supervisor de processo."

    old_pid = supervisor._popen.pid if supervisor._popen else 0
    assert old_pid > 0 and supervisor.is_alive()

    # Rastreia para garantir limpeza no encerramento do teste
    proc = psutil.Process(old_pid)
    process_cleanup_tracker.append(proc)

    start_time = time.time()
    # Injeta a falha: mata o processo abruptamente via kernel
    proc.kill()
    try:
        proc.wait(timeout=2.0)
    except psutil.TimeoutExpired:
        pass
    assert not supervisor.is_alive()

    # Dispara a auto-cura
    restarted = supervisor.restart(reason="Auto-cura após injeção de falha")
    elapsed = time.time() - start_time

    assert restarted, "O processo deveria ter sido reiniciado pelo supervisor."
    assert supervisor.is_alive(), "O processo filho deve estar ativo novamente."
    assert elapsed <= 5.0, f"Tempo de recuperação ({elapsed:.2f}s) excedeu o teto de 5s."

    # Adiciona o novo processo ao rastreador de limpeza
    if supervisor._popen:
        process_cleanup_tracker.append(psutil.Process(supervisor._popen.pid))
    supervisor.terminate_tree()


def test_heartbeat_drop_detection_and_reconnection() -> None:
    """Verifica a detecção de perda de pulso e a transição para estado de recuperação."""
    failure_reasons: List[str] = []
    config = HeartbeatConfig(interval_seconds=0.1, timeout_seconds=0.15, max_missed_pings=2)
    hb = HeartbeatManager(config=config, on_failure_callback=failure_reasons.append)

    # Simula 2 batimentos sem resposta
    hb.create_ping_payload()
    time.sleep(0.2)
    assert hb.check_health()  # 1º ping perdido

    hb.create_ping_payload()
    time.sleep(0.2)
    assert not hb.check_health()  # 2º ping perdido -> falha confirmada
    assert not hb.is_healthy
    assert len(failure_reasons) == 1

    # Auto-cura via registro de pong
    hb.record_pong()
    assert hb.is_healthy
    assert hb.missed_count == 0


def test_resilience_message_buffer_and_backoff_cap() -> None:
    """Verifica a retenção de comandos no buffer e o teto máximo de 5s no backoff."""
    resilience = ResilienceManager()
    assert resilience.state == ConnectionState.STOPPED

    # Injeção de desconexão
    delay = resilience.handle_disconnect("Queda de WebSocket simulada")
    assert resilience.state == ConnectionState.RECOVERING
    assert delay <= 5.0, f"O delay ({delay}s) ultrapassou o teto estrito de 5.0s."

    # Enfileira comandos durante a instabilidade
    cmd1 = resilience.enqueue_command({"action": "click", "selector": "#btn"})
    cmd2 = resilience.enqueue_command({"action": "type", "text": "teste"})
    assert cmd1 is not None and cmd2 is not None
    assert not resilience.buffer.is_empty()

    # Recuperação do sinal e descarregamento das mensagens retidas
    recovered_msgs = resilience.handle_connected()
    assert resilience.state == ConnectionState.CONNECTED
    assert len(recovered_msgs) == 2
    assert recovered_msgs[0].payload["action"] == "click"
    assert resilience.buffer.is_empty()


def test_message_buffer_ttl_expiration() -> None:
    """Verifica que mensagens com TTL expirado são devidamente expurgadas."""
    buffer = MessageBuffer(default_ttl=0.2)
    buffer.push("msg_curta", ttl_seconds=0.1)
    time.sleep(0.15)
    # A mensagem deve ser descartada por expiração
    assert buffer.pop() is None
