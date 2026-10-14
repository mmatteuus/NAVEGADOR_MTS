"""Suíte Adversarial de Caos em Processos e Estruturas de Dados Centrais.

Valida encerramento em cascata de processos netos (0 órfãos),
concorrência massiva no MessageBuffer e limites estritos do Backoff (<= 5.0s).
"""

from __future__ import annotations

import sys
import threading
import time
from typing import List
import psutil

from src.core.message_buffer import MessageBuffer
from src.core.resilience import ExponentialBackoff
from src.core.supervisor import ProcessSupervisor


def test_adversarial_process_tree_termination(process_cleanup_tracker: List[psutil.Process]) -> None:
    """Verifica que matar o processo supervisor encerra todos os subprocessos netos."""
    script = (
        "import subprocess, sys, time\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "time.sleep(60)\n"
    )
    cmd = [sys.executable, "-c", script]
    supervisor = ProcessSupervisor(command=cmd, name="parent_adversarial", restart_delay=0.1)

    assert supervisor.start(), "Falha ao iniciar supervisor com árvore de processos."
    parent_pid = supervisor._popen.pid if supervisor._popen else 0
    assert parent_pid > 0

    parent_proc = psutil.Process(parent_pid)
    process_cleanup_tracker.append(parent_proc)

    # Aguarda o filho neto ser criado
    time.sleep(0.5)
    children = parent_proc.children(recursive=True)
    assert len(children) >= 1, "Processo neto não foi criado."
    grandchild_pid = children[0].pid

    # Finalização adversarial em árvore
    start_t = time.time()
    supervisor.terminate_tree(timeout=2.0)
    elapsed = time.time() - start_t

    assert elapsed <= 3.0, f"Tempo de finalização ({elapsed:.2f}s) excedeu tolerância."
    assert not psutil.pid_exists(parent_pid), f"Processo pai {parent_pid} sobreviveu como órfão!"
    assert not psutil.pid_exists(grandchild_pid), f"Processo neto {grandchild_pid} sobreviveu como órfão!"


def test_adversarial_message_buffer_concurrency_stress() -> None:
    """Submete o MessageBuffer a 10 threads simultâneas disparando 2.000 mensagens."""
    buffer = MessageBuffer(max_capacity=50, default_ttl=0.2)
    erros: List[Exception] = []

    def worker(worker_id: int) -> None:
        try:
            for i in range(200):
                buffer.push({"worker": worker_id, "seq": i})
                if i % 10 == 0:
                    buffer.pop()
                if i % 25 == 0:
                    buffer.cleanup_expired()
        except Exception as exc:
            erros.append(exc)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(erros) == 0, f"Erros de concorrência detectados: {erros}"
    assert len(buffer) <= 50, f"Buffer estourou capacidade máxima: {len(buffer)}"


def test_adversarial_exponential_backoff_strict_bounds() -> None:
    """Verifica 2.000 amostras do algoritmo de backoff garantindo que jamais excede 5.0s."""
    backoff = ExponentialBackoff(initial=0.5, multiplier=2.0, max_delay=5.0, jitter_factor=0.2)
    for _ in range(2000):
        delay = backoff.next_delay()
        assert delay <= 5.0, f"VIOLAÇÃO CRÍTICA: Delay de {delay}s excedeu o teto estrito de 5.0s!"
        assert delay >= 0.2, f"Delay de {delay}s abaixo do piso mínimo razoável."
